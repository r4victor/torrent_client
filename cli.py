import sys
import time
from threading import Thread, Lock

from modules.client import Client

lock = Lock()


def main():
    client = Client()
    t = Thread(target=print_torrents_info, args=(client,))
    t.start()
    while True:
        input()
        with lock:
            command = input('>')
        if command == 'exit':
            client.exit()
            break
        elif command == 'help':
            print_message(get_help_output())
        else:
            try:
                client.change_torrent_status(*parse_command(command))
            except IndexError:
                print_message('Error: There is no torrent with '
                              'corresponding index.')
            except Exception:
                print_message('Error: Unsupported command format.')


def parse_command(command):
    parts = command.split(' ', 1)
    torrent_num = int(parts[0])
    if len(parts) == 1:
        return torrent_num, None
    files_nums = [int(num) for num in parts[1].split(',')]
    return torrent_num, files_nums


def print_torrents_info(client):
    while client.running:
        with lock:
            print("\033[H\033[J")
            print(get_torrents_info_output(client.get_torrents_info()))
        time.sleep(1)


def get_torrents_info_output(torrents_info):
    def get_status(skip):
        return 'skip' if skip else 'download'

    output = (' # | name | active | peers | speed | downloaded | '
              'uploaded | size | completed\n\n')
    line = ('\n {number} | {name} | {active} | {peers} | '
            '{speed} KB/s | {downloaded} MB | {uploaded} MB | '
            '{length} MB | {completed}\n')
    for info in torrents_info:
        output += line.format(**info)
        for index, file in enumerate(info['files']):
            output += '\t{}. {} | {}\n'.format(index + 1, file['path'],
                                               get_status(file['skip']))
    return output + '\n\nPress Enter to get in input mode'


def get_help_output():
    output = ('\n' + '_'*40 +
              '\n\nTo start or stop downloading enter a torrent number. '
              'If you don\'t want to download all files in a package, '
              'use the following syntax: \n\n"<torrent number> '
              '<files numbers separated by comma>"\n\n'
              'To close the client use command "exit". In this case '
              'all data will be saved correctly.\n\n' + '_'*40 + '\n')
    return output


def print_message(text):
    with lock:
        print('\n{}\n'.format(text))
        input()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print(get_help_output())
    else:
        main()
