from pyicloud import PyiCloudService
from shutil import copyfileobj
import os
from os import mkdir, path
from dotenv import load_dotenv

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
    code = input("Enter the code you received of one of your approved devices: ")
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

for album in api.photos.albums:
    try:
        mkdir(album_subdirectory + album)
    except:
        pass

    if album == 'All Photos':
        continue

    for photo in api.photos.albums[album].photos:
        download = ''
        try:
            download = photo.download()
        except:
            continue
        photo_path = album_subdirectory + album + '/' + photo.filename
        with open(photo_path, 'wb') as opened_file:
            print("writing " + photo_path)
            copyfileobj(download.raw, opened_file)
            if path.getsize(photo_path) == photo.size:
                res = photo.delete()
                if not res.ok:
                    print("failed to delete " + photo.filename + " in album " + album) 

