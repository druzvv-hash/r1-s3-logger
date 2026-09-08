# SD file download (PANEL v0.16)

The device panel now lists directories and downloads existing files from microSD.
The normal firmware only reads the card. Session recording remains P5; this feature
also retrieves the existing hardware-test files without removing the card.

## User flow

Open **Файли SD**, choose **Оновити список**, then **Завантажити** beside a file.
Folders have an **Відкрити** button; **На рівень вище** returns to the parent.
Six entries are returned per page. **Ще файли** continues the directory session.
The browser download manager displays progress, cancellation and the final result.
No deletion, formatting or card uploads are exposed.

USB uses the existing loopback bridge. Wi-Fi uses the ESP AP panel; its download
route redirects to a dedicated server on port 81 so a long transfer does not occupy
the main panel server on port 80. UART and HTTP remain on core 0. A lower-priority
SD task on core 1 owns runtime mount/read/close operations, separate from acquisition
and the I2C owner. Runtime SD diagnostics also use this owner.

## Transfer contract

- `GET /api/files?command=LIST%20<path-hex>` opens a directory and returns the first
  page; `NEXT <session>` continues it. Entries contain literal name, directory flag,
  byte size and hexadecimal UTF-8 absolute SD path.
- `OPEN <path-hex>` returns a random nonzero session ID, size and 2048-byte block limit.
- `READ <session> <offset>` returns session, size, offset, data hex and IEEE CRC32.
- `CLOSE <session>` releases the card. Completed directory enumeration closes itself.
- `GET /api/download?path=<path-hex>` streams an attachment with its original name and
  exact Content-Length. USB endpoints additionally require the current session token.
- UART carries these commands as `PANEL <request-id> FILES <command>`; its existing
  request lock is released between chunks so state/live polling can interleave.

USB verifies every chunk's session, offset, size, exact byte count and CRC before
sending it to the browser. A mid-transfer error closes the HTTP connection before
Content-Length is satisfied, leaving a failed/incomplete download. There is no
automatic retry that could mix different files or boots. Restart an interrupted
download from the beginning. Native Wi-Fi streams the same bounded SD reads using
TCP transport integrity. Neither ESP nor bridge buffers the whole file.

One file/directory session is active at a time. Concurrent opens and SD rechecks
receive a busy response. Idle sessions expire after 30 seconds; downloading a file
closes that browser's directory cursor. Refresh the directory to enumerate again.
Paths reject traversal, control characters, backslashes and drive prefixes; paths
longer than 239 bytes appear disabled. Filenames are rendered as text in the UI.

## Integration boundary

The [v0.18 recorder](P5_RECORDING.md) uses the same SD owner and excludes all file
requests before it starts writing. START is refused while a transfer is open;
downloads require READY or ERROR after storage has closed. There is no active-file
snapshot. Sampling continues while downloading, but UART bandwidth limits live delivery and USB transfer
speed; a 1 GiB file will take a long time at 115200 baud with hex framing.

## Validation

Host tests cover binary and empty downloads, Unicode attachment names, traversal and
command rejection, wrong session/offset/size, bad CRC, short chunks and disconnects.
Browser acceptance covers listing, literal filenames, folders, downloading bytes and
mobile layout. Hardware results are recorded in R1_MIGRATION.md after deployment.
