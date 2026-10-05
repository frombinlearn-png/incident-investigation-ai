import argparse
import asyncio
import json
from pathlib import Path

import httpx


async def run_demo(base_url: str, scenario: str) -> int:
    path = Path(__file__).parent / "data" / "incidents" / f"{scenario}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    async with httpx.AsyncClient(base_url=base_url, timeout=35) as client:
        try:
            response = await client.post("/v1/investigations", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            print(f"API returned HTTP {error.response.status_code}: {error.response.text}")
            return 1
        except httpx.RequestError:
            print("Could not reach the API. Start the server and check --base-url.")
            return 1
    print(json.dumps(response.json(), indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a synthetic incident to the running API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--scenario", choices=["database-pool", "aem-cache", "unknown"], default="database-pool"
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_demo(args.base_url, args.scenario)))


if __name__ == "__main__":
    main()
