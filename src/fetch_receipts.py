import os
import re
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from urllib.error import HTTPError
from urllib.request import urlretrieve

from humanize import naturalsize
import numpy as np
import pandas as pd

from itertools import islice
from multiprocessing import Pool


class Receipts(object):

    def __init__(self, target):
        self.target = target

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    REGEX = r'^[\d-]{11}(current-year|last-year|previous-years).xz$'

    def __call__(self):
        return self.receipts

    def datasets(self):
        """List generator with the full path of each CSV/dataset."""
        for file_name in os.listdir(self.DATA_DIR):
            if re.compile(self.REGEX).match(file_name):
                yield os.path.join(self.DATA_DIR, file_name)

    def all(self):
        """
        List generator with Receipt named tuples containing the path of the
        receipt image (to be used when saving it, for example) and the URL of
        the receipt at the Lower House servers.
        """
        dtype = {
            'document_id': np.str,
            'congressperson_id': np.str,
            'congressperson_document': np.str,
            'term_id': np.str,
            'cnpj_cpf': np.str,
            'reimbursement_number': np.str
        }
        for dataset in self.datasets():
            data = pd.read_csv(dataset, parse_dates=[16], dtype=dtype)
            yield from(Receipt(row, self.target) for row in data.itertuples() if not pd.isnull(row.document_id))


class Receipt:

    def __init__(self, receipt, target):
        """
        :param receipt: a Pandas DataFrame row as a NamedTuple (see
        `itertuples` method)
        """
        self.applicant_id = receipt.applicant_id
        self.year = receipt.year
        self.document_id = receipt.document_id
        self.target = target

    def path(self):
        """
        Given a target directory (string), it returns the absolute path to the
        receipt (the path to be used when saving the file).
        """
        return os.path.join(
            os.path.abspath(self.target),
            str(self.applicant_id),
            str(self.year),
            str(self.document_id) + '.pdf'
        )

    @property
    def url(self):
        """
        Returns the URL of this receipt at the Lower House server.
        """
        base = 'http://www.camara.gov.br/cota-parlamentar/documentos/publ/'
        recipe = '{base}{applicant_id}/{year}/{document_id}.pdf'
        return recipe.format(
            base=base,
            applicant_id=self.applicant_id,
            year=self.year,
            document_id=self.document_id
        )


def run(target, limit=None):
    """
    :param target: (string) path to the directory to save the receipts
    :param limit: (int) limit the amount of receipts to fecth
    """
    target = target
    limit = limit
    progress = {
        'count': 0,
        'size': 0,
        'errors': list(),
        'skipped': list()
    }

    # check if target directory exists
    if not os.path.exists(target):
        raise RuntimeError('Directory {} does not exist'.format(target))
        sys.exit()

    # check if target directory is a directory (not a file)
    if not os.path.isdir(target):
        raise RuntimeError('{} is a file, not a directory'.format(target))
        sys.exit()

    # save receipts
    with Pool(processes=4) as pool:
        receipts = Receipts(target=target).all()
        while True:
            cur_receipts = receipts
            if limit:
                cur_receipts = islice(receipts, limit - progress['count'])
            for result in pool.imap(download_receipt, cur_receipts):
                status, receipt, args = result
                if status == 'ok':
                    progress['count'] += 1
                    progress['size'] += int(args['Content-Length'])
                elif status == 'skipped':
                    progress['skipped'].append(receipt.url)
                elif status == 'error':
                    progress['errors'].append(receipt.url)

                raw_msg = '==> Downloaded {:,} files ({}). {}/{} skipped/errors                 '
                msg = raw_msg.format(
                    progress['count'],
                    naturalsize(progress['size']),
                    len(progress['skipped']),
                    len(progress['errors'])
                )
                print(msg, end='\r')

            # exit condition
            if not limit or progress['count'] >= limit:
                break
    return progress

def download_receipt(receipt):
    path = receipt.path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        try:
            file_name, header = urlretrieve(receipt.url, path)
            return ('ok', receipt, header)
        except HTTPError as e:
            return ('error', receipt, repr(e))
    else:
        return ('skipped', receipt, receipt.url)

def print_report(progress):
    # print summary
    msg = '==> Downloaded {:,} files ({})                                     '
    print(msg.format(progress['count'], naturalsize(progress['size'])))

    # print errors
    if progress['errors']:
        msg = '\n==> {:,} receipts could not be saved:'
        print(msg.format(len(progress['errors'])))
        for index, url in enumerate(progress['errors']):
            print('    {}. {}'.format(index + 1, url))

    # print skipped files (already existing)
    if progress['skipped']:
        msg = '\n==> {:,} receipts were skipped (probably they already exist)'
        print(msg.format(len(progress['skipped'])))
        for index, url in enumerate(progress['skipped']):
            print('    {}. {}'.format(index + 1, url))

if __name__ == '__main__':

    # set argparse
    description = """
    This script downloads the receipt images from the Lower House server.

    Be aware that downloading everything might use more than 1 TB of disk
    space.  Because of that you have to specify one `target` directory (where
    to save the files) and optionally you can specify with `--limit` the number
    of images to be downloaded.

    If the `target` directory exists and already has some saved receipts,
    these receipts will not be downloaded again (and they will not count when
    using `--limit` either).

    In other words, if you already have 42 receipts in your target folder,
    running the command with a limit of 8 will end up in a directory with 50
    files: the 42 you already had and 8 freshly downloaded ones.
    """
    parser = ArgumentParser(
        description=description,
        formatter_class=RawTextHelpFormatter
    )
    parser.add_argument('target', help='Directory where images will be saved.')
    parser.add_argument('-l', '--limit', default=0, type=int,
                        help='Limit the number of receipts to be saved')
    args = parser.parse_args()

    # run
    result = run(args.target, args.limit)
    print_report(result)
