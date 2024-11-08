while getopts e: flag
do
    case "${flag}" in
        e) PIO_ENV=${OPTARG};;
    esac
done

echo -D__GIT_HASH__=\\\"$(git rev-parse --short --verify HEAD)\\\"
echo -D__GIT_BRANCH__=\\\"$(git rev-parse --abbrev-ref HEAD)\\\"
echo -D__ISO_DATE__=\\\"$(date +%Y-%m-%dT%H:%M:%SZ)\\\"
echo -D__PIO_ENV__=\\\"$PIO_ENV\\\"

