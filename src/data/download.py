"""Download only issues.csv from Mendeley Help Desk Tickets v3 (CC BY 4.0)."""

from pathlib import Path
import requests

from src.config import Paths

SOURCE_URL = "https://data.mendeley.com/public-files/datasets/btm76zndnt/files/2018b884-181a-482b-8a06-a86bbf41f4e7/file_downloaded?dl=1"
EXPECTED_BYTES = 20_586_538


def download() -> Path:
    target = Paths.raw_mendeley / "issues.csv"
    if target.exists() and target.stat().st_size == EXPECTED_BYTES:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".csv.part")
    with requests.get(SOURCE_URL, stream=True, timeout=(15, 60), headers={"User-Agent": "Mozilla/5.0"}) as response:
        response.raise_for_status()
        with partial.open("wb") as stream:
            for chunk in response.iter_content(1 << 20):
                stream.write(chunk)
    if partial.stat().st_size != EXPECTED_BYTES:
        raise RuntimeError("Downloaded issues.csv differs from the published v3 file size.")
    partial.replace(target)
    print(f"Source ready: {target.name} ({EXPECTED_BYTES:,} bytes)")
    return target


if __name__ == "__main__":
    download()
