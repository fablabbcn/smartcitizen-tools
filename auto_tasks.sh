#!/bin/bash

watched_files="$1"  # pass watched files as cmd line arguments

if [ -z "$watched_files" ]; then
    echo "Nothing to watch, abort"
    exit
else
    echo "Watching: $watched_files"
fi

previous_checksum="dummy"
while [ 1 ]; do

    case "$OSTYPE" in
        darwin*)  checksum=$(md5 $watched_files | md5) ;; 
        linux*)   checksum=$(md5sum $watched_files | md5sum) ;;
    esac

    if [ "$checksum" != "$previous_checksum" ]; then
        echo "File change detected..."
        if grep -i Smartcitizen "$watched_files" ; then
            echo "Found SmartCitizen..."
            sleep 2
            echo "Getting firmware version..."
            cd ..
            firmVer=$(python tools/get_info.py --sam --esp)
            sam_firmVer=$(echo $firmVer | head -n 1 | cut -c 7-13)
            esp_firmVer=$(echo $firmVer | tail -n 1 | cut -c 7-13)
            echo "SAM firmware version: "$sam_firmVer
            echo "ESP firmware version: "$esp_firmVer

            currentVer=$(git rev-parse HEAD | cut -c 1-7)
            echo "Firmware latest version: "$currentVer

            if [ "$sam_firmVer" != "$currentVer" ]; then
                echo "Flashing SAM..."
                python make.py flash sam -v
                sleep 5
            fi

            if [ "$esp_firmVer" != "$currentVer" ]; then
                echo "Flashing ESP..."
                python make.py flash esp -v
                sleep 5
            fi

            #Only need to execute if option is present
            if test "$2" = "--co2"; then
                echo "CO2..."
                python tools/co2.py -v --margin 10 --stab-time 300

                case "$OSTYPE" in
                    darwin*)  osascript -e 'display notification "CO2 sensor done!" with title "Smart Citizen"' ;; 
                    linux*)   echo "Not yet!" ;;
                esac
            fi

            cd tools/
            echo "Done for this kit!"
            case "$OSTYPE" in
                darwin*)  osascript -e 'display notification "SCK done!" with title "Smart Citizen"' ;; 
                linux*)   echo "Not yet!" ;;
            esac
        fi
    fi
    previous_checksum="$checksum"
    sleep 1
done
