"""Google Drive: archive uploads, and temporary public links for Instagram Login accounts."""
from __future__ import annotations

from datetime import date

from . import config, google_auth

FOLDER_MIME = "application/vnd.google-apps.folder"


def _q(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def ensure_folder(drive, folder_path: str) -> str:
    parent = "root"
    for name in [p for p in folder_path.split("/") if p]:
        q = f"name = '{_q(name)}' and mimeType = '{FOLDER_MIME}' and '{parent}' in parents and trashed = false"
        found = drive.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files", [])
        if found:
            parent = found[0]["id"]
        else:
            body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent]}
            parent = drive.files().create(body=body, fields="id").execute()["id"]
    return parent


def direct_url(file_id: str) -> str:
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"


def upload(path: str, folder: str = "Social Uploads", dated_subfolder: bool = True, share_public: bool = False, drive=None) -> dict:
    from googleapiclient.http import MediaFileUpload

    f = config.local_file(path)
    drive = drive or google_auth.service("drive", "v3")
    folder_path = f"{folder}/{date.today().isoformat()}" if dated_subfolder else folder
    parent = ensure_folder(drive, folder_path)
    meta = drive.files().create(
        body={"name": f.name, "parents": [parent]},
        media_body=MediaFileUpload(str(f), resumable=True, chunksize=8 * 1024 * 1024),
        fields="id,name,webViewLink",
    ).execute()
    out = {"file_id": meta["id"], "name": meta["name"], "folder": folder_path, "web_link": meta.get("webViewLink")}
    if share_public:
        out.update(share(meta["id"], drive=drive))
    return out


def share(file_id: str, drive=None) -> dict:
    drive = drive or google_auth.service("drive", "v3")
    perm = drive.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}, fields="id").execute()
    return {"permission_id": perm["id"], "direct_url": direct_url(file_id)}


def unshare(file_id: str, permission_id: str, drive=None) -> None:
    drive = drive or google_auth.service("drive", "v3")
    drive.permissions().delete(fileId=file_id, permissionId=permission_id).execute()
