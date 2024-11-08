import subprocess
import datetime
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--env", default=None, help="The platformio environment"
    )

    args = parser.parse_args()

    revision = (
        subprocess.check_output(["git", "rev-parse", "--short", "--verify", "HEAD"])
        .strip()
        .decode("utf-8")
    )

    iso_date = datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z'

    print("-D__GIT_HASH__='\"%s\"'" % revision)
    print("-D__ISO_DATE__='\"%s\"'" % iso_date)
    if args.env is not None:
        print("-D__PIO_ENV__='\"%s\"'" % args.env)





