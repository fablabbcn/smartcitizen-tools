import subprocess
import datetime

revision = (
    subprocess.check_output(["git", "rev-parse", "--short", "--verify", "HEAD"])
    .strip()
    .decode("utf-8")
)

iso_date = datetime.date.today().isoformat()

print("-D__GIT_HASH__='\"%s\"'" % revision)
print("-D__ISO_DATE__='\"%s\"'" % iso_date)