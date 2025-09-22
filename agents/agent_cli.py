
import argparse
import json
import pathlib

HERE = pathlib.Path(__file__).parent

def load(p: str) -> str:
    return pathlib.Path(p).read_text(encoding='utf-8')

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["new_feature", "bugfix"], required=True)
    ap.add_argument("--prompt-file")
    args = ap.parse_args()
    system = load(HERE / "prompts" / "system.md")
    task = load(HERE / "prompts" / f"task_{args.task}.md")
    user = load(args.prompt_file) if args.prompt_file else ""
    print(
        json.dumps(
            {
                "system": system,
                "task": task,
                "user": user,
                "config_path": str(HERE / "config.yaml"),
                "repo_root": str((HERE / "..").resolve()),
            },
            indent=2,
        )
    )

if __name__ == "__main__":
    main()
