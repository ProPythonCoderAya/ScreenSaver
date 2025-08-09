import json
import re
import shutil
import zipfile
import io

import requests
import argparse
import os

def abspath(path):
    if path.startswith("/"):
        return path
    else:
        return os.path.join(os.path.dirname(__file__), path)

class UpdateChecker:
    def __init__(self, gituser, gitrepo, gitrepoversionfile, localversionfile):
        self.user = gituser
        self.repo = gitrepo
        self.version_git = gitrepoversionfile
        self.version_local = localversionfile
        self.url = f"https://raw.githubusercontent.com/{gituser}/{gitrepo}/main/{gitrepoversionfile}"

    @staticmethod
    def is_valid_version(version):
        return bool(re.compile(r"^v\d+(\.\d+){0,2}$").match(version))

    def __fetch(self):
        """ Fetches the remote version file """
        try:
            response = requests.get(self.url)
        except requests.exceptions.ConnectionError:
            return -1
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error while fetching from {self.url}, status code: {response.status_code}")

    def __local(self):
        if os.path.exists(self.version_local):
            try:
                with open(self.version_local) as f:
                    data = json.load(f)

                version: str = data["version"]

                if not self.is_valid_version(version):
                    print("Version is corrupted")
                else:
                    return version

            except Exception as e:
                print(f"Failed to load local version: {e}")

        version = "v0.0.0"
        with open(self.version_local, "w") as f:
            json.dump({"version": version}, f, indent=4)
        return version

    def check(self) -> tuple[bool, str, str] | int:
        local_version = self.__local()
        remote_version = self.__fetch()
        if remote_version == -1:
            return -1
        remote_version = remote_version["version"]

        return local_version != remote_version, local_version, remote_version

def update(version):
    url = f"https://raw.githubusercontent.com/ProPythonCoderAya/ScreenSaver/main/update/versions/{version}/ScreenSaver.zip"
    print(f"Downloading update from {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to get update: {e}")
        return 1

    # Extract ZIP from bytes into update/
    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zipf:
            zipf.extractall(abspath("update/"))
        print("Extracted update zip")
    except zipfile.BadZipFile as e:
        print(f"Bad ZIP file: {e}")
        return 1

    # Apply the update safely
    try:
        src_dir = "update"
        dst_dir = os.path.abspath("../..")  # This is ../

        for root, dirs, files in os.walk(src_dir):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src_dir)  # Relative path from update/
                dst_path = os.path.join(dst_dir, rel_path)  # New path in ../

                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

        with open("version.json", "w") as f:
            json.dump({"version": version}, f, indent=4)

        shutil.rmtree(src_dir)

        print("Update applied successfully!")
    except Exception as e:
        print(f"Failed to apply update: {e}")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", required=True, type=str)

    args = parser.parse_args()
    version = args.version

    exit(update(version))

if __name__ == '__main__':
    main()
