
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(_BACKEND_DIR / ".env")

from database.database import sessions_col
from services.cloudinary_service import upload_image_bytes


def main() -> None:
    images_dir = _BACKEND_DIR / "images"
    if not images_dir.exists():
        print(f"No images directory at {images_dir}; nothing to migrate.")
        return

    url_by_ref: dict[str, str] = {}
    files = sorted(p for p in images_dir.glob("*") if p.is_file())
    print(f"Found {len(files)} image file(s) in {images_dir}.")
    for p in files:
        try:
            url = upload_image_bytes(p.read_bytes(), filename=p.name, prompt=p.stem)
            url_by_ref[f"images/{p.name}"] = url
            print(f"  uploaded {p.name} -> {url}")
        except Exception as e: 
            print(f"  FAILED  {p.name}: {e}")

    if not url_by_ref:
        print("Nothing uploaded; aborting DB rewrite.")
        return

    updated = 0
    for doc in sessions_col().find({"notes_markdown": {"$regex": r"images/"}}):
        md = doc.get("notes_markdown") or ""
        new_md = md
        for ref, url in url_by_ref.items():
            new_md = new_md.replace(ref, url)
        if new_md != md:
            sessions_col().update_one(
                {"_id": doc["_id"]}, {"$set": {"notes_markdown": new_md}}
            )
            updated += 1
            print(f"  rewrote session {doc['_id']}")

    print(f"\nDone. Uploaded {len(url_by_ref)} image(s); rewrote {updated} session(s).")
    print("You can now delete Backend/images/ and the stray Backend/*.md files.")


if __name__ == "__main__":
    main()
