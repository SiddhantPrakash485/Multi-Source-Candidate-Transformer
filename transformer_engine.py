import json
import re

class Normalizer:
    """Handles data formatting standardizations."""
    @staticmethod
    def phone_e164(phone_str):
        if not phone_str: return None
        cleaned = re.sub(r'\D', '', phone_str)
        return f"+{cleaned}" if len(cleaned) >= 10 else None

class CandidateProfile:
    """The internal canonical record for a candidate."""
    def __init__(self):
        self.data = {
            "emails": [],
            "phones": [],
            "skills": [],
            "links": {},
            "provenance": []
        }
        self.confidence_scores = {}

    def merge_scalar(self, field, value, source, confidence):
        """For flat fields like name, headline, location."""
        current_conf = self.confidence_scores.get(field, 0)
        if confidence > current_conf and value is not None:
            self.data[field] = value
            self.confidence_scores[field] = confidence
            self.data["provenance"].append({
                "field": field, 
                "source": source, 
                "method": "highest_confidence"
            })

    def merge_skills(self, new_skills):
        """Union and deduplicate skills based on skill name."""
        existing_skills = {s["name"]: s for s in self.data["skills"]}
        
        for skill in new_skills:
            name = skill["name"]
            if name in existing_skills:
                # If skill exists, append the source if it's new
                if skill["sources"][0] not in existing_skills[name]["sources"]:
                    existing_skills[name]["sources"].extend(skill["sources"])
            else:
                existing_skills[name] = skill
                
        self.data["skills"] = list(existing_skills.values())

    def merge_links(self, new_links):
        """Merge dictionary of links."""
        for platform, url in new_links.items():
            if platform not in self.data["links"]:
                self.data["links"][platform] = url

class DataSource:
    """Base class for all extractors."""
    def __init__(self, raw_data, confidence_weight):
        self.raw_data = raw_data
        self.confidence_weight = confidence_weight

    def extract(self) -> dict:
        raise NotImplementedError

class ATSJsonSource(DataSource):
    """Extracts data from a structured ATS JSON payload."""
    def extract(self):
        try:
            data = json.loads(self.raw_data)
            return {
                "full_name": data.get("candidate_name"),
                "emails": [data.get("contact_email")] if data.get("contact_email") else [],
                "phone": data.get("phone_number"),
                "source": "ATS_JSON"
            }
        except json.JSONDecodeError:
            return None # Fails gracefully

class GitHubSource(DataSource):
    """Extracts candidate data from a GitHub API user profile response."""
    def extract(self):
        try:
            data = json.loads(self.raw_data)
            
            # Map GitHub 'languages' into our canonical skills format
            skills = []
            for lang in data.get("languages", []):
                skills.append({
                    "name": lang.lower(),
                    "confidence": self.confidence_weight,
                    "sources": ["GitHub"]
                })
            
            return {
                "full_name": data.get("name"),
                "emails": [data.get("email")] if data.get("email") else [],
                "headline": data.get("bio"),
                "links": {"github": data.get("html_url")},
                "skills": skills,
                "source": "GitHub_API"
            }
        except json.JSONDecodeError:
            return None

class PipelineEngine:
    """Ingests sources and merges them into canonical profiles."""
    def __init__(self):
        self.profiles = {} # Keyed by primary email

    def ingest(self, sources):
        for source in sources:
            extracted = source.extract()
            if not extracted:
                continue
            
            # Identify candidate by email (Primary matching key)
            primary_email = extracted.get("emails", [None])[0]
            if not primary_email:
                continue
                
            if primary_email not in self.profiles:
                self.profiles[primary_email] = CandidateProfile()
            
            profile = self.profiles[primary_email]
            weight = source.confidence_weight
            src_name = extracted["source"]
            
            # Merge Emails
            for em in extracted.get("emails", []):
                if em not in profile.data["emails"]:
                    profile.data["emails"].append(em)

            # Merge Scalars
            for field in ["full_name", "headline"]:
                if field in extracted and extracted[field]:
                    profile.merge_scalar(field, extracted[field], src_name, weight)
            
            # Normalize and merge phone
            if "phone" in extracted and extracted["phone"]:
                norm_phone = Normalizer.phone_e164(extracted["phone"])
                if norm_phone and norm_phone not in profile.data["phones"]:
                    profile.data["phones"].append(norm_phone)
                    profile.data["provenance"].append({
                        "field": "phones", "source": src_name, "method": "normalized_append"
                    })

            # Merge Arrays/Dicts
            if "skills" in extracted:
                profile.merge_skills(extracted["skills"])
            if "links" in extracted:
                profile.merge_links(extracted["links"])

class ProfileProjector:
    """Shapes the canonical profile into the final output based on runtime config."""
    
    def __init__(self, config):
        self.config = config
        self.on_missing = config.get("on_missing", "null")
        self.include_confidence = config.get("include_confidence", False)

    def _extract_value(self, data, path):
        """
        A lightweight parser for basic JSON paths.
        Handles: 'full_name', 'emails[0]', 'skills[].name', 'links.github'
        """
        if not path:
            return None
            
        # Handle dict traversal (e.g., links.github)
        if "." in path and "[]" not in path:
            parts = path.split(".")
            val = data
            for part in parts:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    return None
            return val
        
        # Handle array mappings (e.g., skills[].name)
        if "[]" in path:
            base_key, sub_key = path.split("[]")
            sub_key = sub_key.lstrip(".") 
            
            arr = data.get(base_key, [])
            if not arr: 
                return None
            if sub_key:
                return [item.get(sub_key) for item in arr if isinstance(item, dict) and sub_key in item]
            return arr
            
        # Handle indexed arrays (e.g., emails[0])
        if "[" in path and "]" in path:
            base_key = path[:path.index("[")]
            index = int(path[path.index("[")+1:path.index("]")])
            
            arr = data.get(base_key, [])
            return arr[index] if len(arr) > index else None
            
        # Handle direct key
        return data.get(path)

    def project(self, profile):
        """Applies the configuration to the profile data."""
        raw_data = profile.data
        output = {}
        
        for field_def in self.config.get("fields", []):
            out_path = field_def.get("path")
            in_path = field_def.get("from", out_path) 
            
            val = self._extract_value(raw_data, in_path)
            
            # Handle Missing Values
            is_empty = val is None or (isinstance(val, list) and len(val) == 0)
            
            if is_empty:
                if field_def.get("required") and self.on_missing == "error":
                    raise ValueError(f"CRITICAL: Required field missing: {out_path}")
                elif self.on_missing == "omit":
                    continue
                elif self.on_missing == "null":
                    val = None
                    
            output[out_path] = val

        # Toggle Confidence
        if self.include_confidence:
            scores = profile.confidence_scores.values()
            output["overall_confidence"] = round(sum(scores) / len(scores), 2) if scores else 0.0
            
        return output