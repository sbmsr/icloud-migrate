from pyicloud import PyiCloudService
from shutil import copyfileobj
import os
from os import mkdir, path
from dotenv import load_dotenv
import filecmp
import hashlib

load_dotenv()

username = os.getenv('username') or input("icloud username: ")
password =  os.getenv('password') or input("icloud password: ")
migration_root = os.getenv('migration_root') or input("desired migration directory: ")

api = PyiCloudService(username, password)
album_subdirectory = migration_root + "/albums/"

try:
    os.makedirs(album_subdirectory)
except:
    pass

if api.requires_2fa:
    print("Two-factor authentication required.")
    code = '' + input("Enter the code you received of one of your approved devices: ")
    result = api.validate_2fa_code(code)
    print("Code validation result: %s" % result)

    if not result:
        print("Failed to verify security code")
        sys.exit(1)

    if not api.is_trusted_session:
        print("Session is not trusted. Requesting trust...")
        result = api.trust_session()
        print("Session trust result %s" % result)

        if not result:
            print("Failed to request trust. You will likely be prompted for the code again in the coming weeks")
elif api.requires_2sa:
    import click
    print("Two-step authentication required. Your trusted devices are:")

    devices = api.trusted_devices
    for i, device in enumerate(devices):
        print( "  %s: %s" % (i, device.get('deviceName',
            "SMS to %s" % device.get('phoneNumber'))))

    device = click.prompt('Which device would you like to use?', default=0)
    device = devices[device]
    if not api.send_verification_code(device):
        print("Failed to send verification code")
        sys.exit(1)

    code = click.prompt('Please enter validation code')
    if not api.validate_verification_code(device, code):
        print("Failed to verify verification code")
        sys.exit(1)

def get_photo_hashes(photo, local_path):
    remote_hash = hashlib.md5(photo.download().content).hexdigest()
    with open(local_path, 'rb') as opened_file:
        content = opened_file.read()
        local_hash = hashlib.md5(content).hexdigest()
    return [remote_hash, local_hash]

def download_and_delete_photo(photo):
    local_photo_path = album_subdirectory + album + '/' + photo.filename
    try:
        with open(local_photo_path, 'wb') as opened_file:
            copyfileobj(photo.download().raw, opened_file)
    except:
        return

    try:
        hashes = get_photo_hashes(photo, local_photo_path)
    except:
        os.remove(local_photo_path)
        return

    if hashes[0] == hashes[1]:
        res = photo.delete()
        if res.ok:
            print("success: " + local_photo_path)
        else:
            print("failed to delete " + photo.filename + " in album " + album) 
    else:
        print("photo hash mismatch: on disk is " + hashes[1] + " - on icloud is " + hashes[0] + ". Moving on . . . ") 
        os.remove(local_photo_path)

for album in api.photos.albums:
    try:
        mkdir(album_subdirectory + album)
    except:
        pass

    if album != 'All Photos':
        continue

    for photo in api.photos.albums[album].photos:
        download_and_delete_photo(photo)

