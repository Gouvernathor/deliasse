# Rework from Deliasse-Demons, by Paula Forteza & Emmanuel Raviart

import argparse
from functools import partial
import json
import logging
import os
from sys import stdout
from threading import Thread, Timer
from time import sleep

import requests


log = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
target_dir = './out'
legislature = 16
refresh = False
organes = None
context_by_organe = {}

timer_period = dict(discussion=900,
                    prochain=2,
                    odj=3600,
                    )

class Context:
    def __init__(self, organe):
        self.need_prochain_a_discuter = True
        self.need_textes_ordre_du_jour = True
        self.numeros_by_bibard_suffixed = {} # dict de bibard vers liste de numeros
        self.organe = organe
        self.sort_by_numeros_by_bibard_suffixed = {} # dict de bibard vers dict de numero vers sort
        self.urgent_task = None # Task à appeler avant les tasks
        self.tasks = [] # Tasks à appeler par la suite

    def add_task(self, *args, **kwargs):
        task = Task(*args, **kwargs)
        if task not in self.tasks:
            self.tasks.append(task)

    def get_amendments(self, bibard, bibard_suffixe, numeros, full=False):
        log.info('get_amendments(bibard={}, bibard_suffixe={}, organe={}, full={})'.format(bibard,
                                                                                           bibard_suffixe,
                                                                                           self.organe,
                                                                                           full))
        bibard_complet = bibard + bibard_suffixe
        assert self.organe in organes

        json_dir = os.path.join(target_dir, f'assemblee{legislature}', self.organe, bibard_complet)
        os.makedirs(json_dir, exist_ok=True)
        obsolete_filenames = {filename for filename in os.listdir(json_dir)
                              if filename.startswith('amendement-') and filename.endswith('.json')}

        while numeros:
            numeros_to_request = numeros[:25]
            numeros = numeros[25:]
            response = requests.get('http://eliasse.assemblee-nationale.fr/eliasse/amendement.do',
                                params=dict(bibard=bibard,
                                            bibardSuffixe=bibard_suffixe,
                                            legislature=legislature,
                                            numAmdt=numeros_to_request,
                                            organeAbrv=self.organe,
                                            ))
            data = response.json()
            assert tuple(data) == ('amendements',) , sorted(data.keys())
            for amendement in data['amendements']:
                numero = amendement['numeroReference']
                json_filename = f'amendement-{numero}.json'
                write_json(amendement, os.path.join(json_dir, json_filename))
                obsolete_filenames.discard(json_filename)

                self.sort_by_numeros_by_bibard_suffixed[bibard_complet][numero] = amendement['sortEnSeance']

        if full:
            for json_filename in obsolete_filenames:
                json_filepath = os.path.join(json_dir, json_filename)
                log.info('  Removing obsolete amendment : {}'.format(json_filepath))
                os.remove(json_filepath)

    def get_discussion(self, bibard, bibard_suffixe):
        log.info('get_discussion(bibard={}, bibard_suffixe={}, organe={})'.format(bibard,
                                                                                 bibard_suffixe,
                                                                                 self.organe))
        bibard_complet = bibard + bibard_suffixe
        data = requests.get('http://eliasse.assemblee-nationale.fr/eliasse/discussion.do',
                            params=dict(bibard=bibard,
                                        bibardSuffixe=bibard_suffixe,
                                        legislature=legislature,
                                        organeAbrv=self.organe,
                                        )).json()
        assert tuple(data) == ('amdtsParOrdreDeDiscussion',) , sorted(data.keys())

        data = data['amdtsParOrdreDeDiscussion']
        write_json(data, os.path.join(target_dir, f'assemblee{legislature}', self.organe, bibard_complet, 'discussion.json'))

        numeros = [resume_amdt['numero'] for resume_amdt in data['amendements']]
        self.numeros_by_bibard_suffixed[bibard_complet] = numeros
        self.sort_by_numeros_by_bibard_suffixed[bibard_complet] = {resume_amdt['numero']: resume_amdt['sort']
                                                                   for resume_amdt in data['amendements']}
        self.add_task(self.get_amendments, bibard=bibard, bibard_suffixe=bibard_suffixe, numeros=numeros, full=True)

        if refresh:
            Timer(timer_period['discussion'], self.add_task, kwargs=dict(function=self.get_discussion,
                                                                         bibard=bibard,
                                                                         bibard_suffixe=bibard_suffixe,
                                                                         )).start()
        return

    def get_prochain_a_discuter(self):
        log.info('get_prochain_a_discuter(organe={})'.format(self.organe))
        data = requests.get('http://eliasse.assemblee-nationale.fr/eliasse/prochainADiscuter.do',
                            cookies=dict(FOSUSED_ORGANE=self.organe),
                            params=dict(organeAbrv=self.organe),
                            ).json()
        assert tuple(data.keys()) == ('prochainADiscuter',)
        data = data['prochainADiscuter']
        write_json(data,
                   os.path.join(target_dir, f'assemblee{legislature}', self.organe, 'prochain_a_discuter.json'))

        if int(data['legislature']) == legislature:
            bibard_suffixed = data['bibard'] + data['bibardSuffixe']
            if (numeros := self.numeros_by_bibard_suffixed.get(bibard_suffixed)) is not None:
                if (numero_a_discuter := data['numAmdt']) in numeros:
                    index = numeros.index(numero_a_discuter)
                    numeros_unsorted = set(numeros[:index])\
                                       - set(self.sort_by_numeros_by_bibard_suffixed[bibard_suffixed])
                    if numeros_unsorted:
                        self.urgent_task = Task(function=self.get_amendments,
                                                bibard=data['bibard'],
                                                bibard_suffixe=data['bibardSuffixe'],
                                                full=False,
                                                numeros=list(numeros_unsorted)+numeros[index:index+2],
                                                ) # TODO check ce +2

        if refresh:
            Timer(timer_period['prochain'], setattr, args=(self, 'need_prochain_a_discuter', True)).start()
        return

    def get_textes_ordre_du_jour(self):
        log.info('get_textes_ordre_du_jour(organe={})'.format(self.organe))
        data = requests.get('http://eliasse.assemblee-nationale.fr/eliasse/textesOrdreDuJour.do',
                            params=dict(organeAbrv=self.organe),
                            ).json()

        write_json(data, os.path.join(target_dir, f'assemblee{legislature}', self.organe, 'ordre-du-jour.json'))

        bibard_suffixeds = {discussion['textBibard']+discussion['textBibardSuffixe'] for discussion in data}
        for key in ('numeros_by_bibard_suffixed', 'sort_by_numeros_by_bibard_suffixed'):
            for bibard_suffixed in tuple(getattr(self, key).keys()):
                if bibard_suffixed not in bibard_suffixeds:
                    del getattr(self, key)[bibard_suffixed]

        for discussion in data:
            self.add_task(function=self.get_discussion,
                          bibard=discussion['textBibard'],
                          bibard_suffixe=discussion['textBibardSuffixe'],
                          )

        if refresh:
            Timer(timer_period['odj'], setattr, args=(self, 'need_textes_ordre_du_jour', True)).start()
        return

    def next_task(self):
        if self.urgent_task is not None:
            task = self.urgent_task
            self.urgent_task = None
        elif self.tasks:
            task = self.tasks.pop(0)
        else:
            task = None
        return task

    def advance(self):
        while True:
            if self.need_prochain_a_discuter:
                self.need_prochain_a_discuter = False
                self.get_prochain_a_discuter()

            elif self.need_textes_ordre_du_jour:
                self.need_textes_ordre_du_jour = False
                self.get_textes_ordre_du_jour()

            elif (task := self.next_task()) is not None:
                task()

            else:
                yield

class Task(partial):
    def __new__(cls, function, **kwargs):
        """
        Allows `function` to be passed by kwarg, and disallows positional args.
        """
        return super().__new__(cls, function, **kwargs)

    def __eq__(self, other):
        if type(self) != type(other):
            return False

        return self.func == other.func and self.keywords == other.keywords


def get_references_organes():
    log.info('get_references_organes()')
    data = requests.get('http://eliasse.assemblee-nationale.fr/eliasse/getListeReferenceDesOrganes.do').json()

    write_json(data, os.path.join(target_dir, f'assemblee{legislature}', 'organes.json'))

    return {reference['value']:reference['text'] for reference in data}


def harvest_organe(organe):
    log.info(f'harvest_organe({organe})')
    context = context_by_organe[organe] = Context(organe)

    for _done in context.advance():
        if refresh:
            sleep(1)
        else:
            break


def _main():
    """
    Should not be called from outside the module.
    Takes the command-line parameters and applies them as globals.
    """
    global target_dir, legislature, refresh

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='verbose mode')
    parser.add_argument('-t', '--target_dir', default=target_dir, help='target directory to write JSON files')
    parser.add_argument('-l', '--legislature', default=legislature, help='target legislature number')
    parser.add_argument('-r', '--refresh', action='store_true', default=refresh, help='refresh the data in a loop')
    parser.add_argument('-o', '--organes', default=None, help='a comma-saparated list of organes to query, '
                                                              'whether a commission or AN for the whole '
                                                              'assembly (all, if not provided)')
    # chambres considérées
    args = parser.parse_args()

    target_dir = args.target_dir

    if args.legislature is not None:
        legislature = args.legislature

    if args.verbose:
        logging.basicConfig(level=logging.INFO, stream=stdout)

    refresh = args.refresh

    if args.organes is not None:
        ar_organes = args.organes.split(',')
        global organes
        try:
            organes = {org: organes[org] for org in ar_organes}
        except KeyError:
            raise ValueError(f'Organe(s) {set(ar_organes)-set(organes)} not found among {organes}')

def run():
    """
    Launches the harvesting process.
    The `organes` global variable should be set before calling this function.
    """
    threads = [Thread(target=harvest_organe, args=(organe,), daemon=True) for organe in organes]
    for thread in threads:
        thread.start()
    while threads:
        # allows for a KeyboardInterrupt to kill every thread at once (along with the daemon thing)
        thread.join(1)
        if not thread.is_alive():
            threads.remove(thread)
            if threads:
                thread = threads[0]


def write_json(data, filepath):
    """
    Writes the JSON `data` to a file at `filepath`, unless
    the file already exists and contains the same data.
    Returns whether the file was (re)written.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    new_text = json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as json_file:
            old_text = json_file.read()
        if new_text == old_text:
            return False
    with open(filepath, 'w', encoding='utf-8') as json_file:
        json_file.write(new_text)
    return True

try:
    organes = get_references_organes()
except Exception:
    pass


if __name__ == "__main__":
    _main()
    run()
