## Overview

This is a command-line client written in pure python without third-party modules and magic.

Package includes:

`cli.py` – command-line interface entry point

`client.py` – client implementation

`bencode.py` – encoding and decoding bencode

`tracker.py` – tracker connection

`files.py` – handling torrent files

`pwp/messages.py` – building and parsing Peer Wire Protocol messages

`pwp/connection.py` – peer connection

## Using

To start or stop downloading enter a torrent number: `2`.
If you don't want to download all files in a package, use the following syntax:

```<torrent number> <files numbers separated by comma>```

To close the client use command `exit`. In this case all data will be saved correctly.

## Features

1. Simultaneous downloads
2. Possibility of downloading individual files
3. Data recovery

## Version

1.0

## Author

Victor Skvortsov
