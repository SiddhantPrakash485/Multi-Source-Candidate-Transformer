import argparse
import json
import sys
import os

# Import the engine components we built previously
from transformer_engine import PipelineEngine, ATSJsonSource, GitHubSource, ProfileProjector

def load_json_file(filepath):
    """Safely loads a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(filepath, 'r') as f:
            return f.read() # Return raw string so the Extractors can handle parsing/errors
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Eightfold Intern Assignment: Multi-Source Candidate Data Transformer"
    )
    
    # Required Configuration
    parser.add_argument('--config', required=True, help="Path to the runtime config JSON file.")
    
    # Optional Input Sources
    parser.add_argument('--ats', help="Path to the ATS JSON source file.")
    parser.add_argument('--github', help="Path to the GitHub JSON source file.")
    
    # Output Control
    parser.add_argument('--out', help="Path to save the output JSON. Prints to console if omitted.")

    args = parser.parse_args()

    # 1. Load the Runtime Config
    if not os.path.exists(args.config):
        print(f"Error: Config file '{args.config}' not found.", file=sys.stderr)
        sys.exit(1)
    
    with open(args.config, 'r') as f:
        try:
            runtime_config = json.load(f)
        except json.JSONDecodeError:
            print("Error: Config file is not valid JSON.", file=sys.stderr)
            sys.exit(1)

    # 2. Ingest Data Sources
    sources = []
    if args.ats:
        raw_ats = load_json_file(args.ats)
        sources.append(ATSJsonSource(raw_ats, confidence_weight=0.9))
        
    if args.github:
        raw_github = load_json_file(args.github)
        sources.append(GitHubSource(raw_github, confidence_weight=0.7))

    if not sources:
        print("Warning: No input sources provided. Please provide --ats or --github.", file=sys.stderr)
        sys.exit(1)

    # 3. Run the Engine
    engine = PipelineEngine()
    engine.ingest(sources)

    # Note: Since this CLI runs a batch of files for a single candidate based on the assignment scope,
    # we just grab the first profile in the dictionary. For scale, you'd iterate through engine.profiles.
    if not engine.profiles:
        print("No valid candidate profiles could be extracted from the provided sources.", file=sys.stderr)
        sys.exit(1)

    # Get the merged profile (assuming one primary candidate for this CLI run)
    primary_email = list(engine.profiles.keys())[0]
    merged_profile = engine.profiles[primary_email]

    # 4. Project and Validate Output
    projector = ProfileProjector(runtime_config)
    try:
        final_output = projector.project(merged_profile)
    except ValueError as e:
        print(f"Projection Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Emit JSON
    json_output = json.dumps(final_output, indent=2)
    
    if args.out:
        with open(args.out, 'w') as f:
            f.write(json_output)
        print(f"Success! Canonical profile saved to {args.out}")
    else:
        print(json_output)

if __name__ == "__main__":
    main()