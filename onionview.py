#!/usr/bin/env python
# -*- Encoding: utf-8 -*-
#
#  OnionView
#
#  Copyright 2016 Kevin Steen <ks@kevinsteen.net>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''OnionView

Usage: onionview [port]

  port : TCP socket port number to connect to.

'''
''' TODO:
+ Display Port in UI
+ Warning against posting screenshots
+ Move Streams if the circuit id has changed ('DETACHED')
+ Remove closed circuits and streams after a time delay
+ Highlight new entries in treeview for 1 second

Reference:
stem library docs: https://stem.torproject.org/
Tor control protocol spec:
    https://gitweb.torproject.org/torspec.git/tree/control-spec.txt
'''
__version_info__ = (0, 0, 1)

TOR_PORTS=(
    9153, # TorMessenger
    9151, # TorBrowserBundle
    9051, # System
    )


import logging
_logger = logging.getLogger(__name__)

try:
    import tkinter as tk
    from tkinter import messagebox
    import tkinter.ttk as ttk
except ImportError:
    import Tkinter as tk
    import tkMessageBox as messagebox
    import ttk

#import time
from collections import defaultdict
from datetime import datetime
import stem.control
import stem

COLORS = {
          'mytext': '#f69454',  #  tangerine
          'theirtext': '#ee693f',  #  carrot
          'msgtextbackgroun': '#fcfdfe',  # off-white
          'daemonbroken': '#cf3721',  # tomato
          'daemonrunning': '#739f3d',  # pear green
         }


def main(argv):
    #~ logging.basicConfig(
                    #~ format='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
                    #~ datefmt = '%H:%M:%S',
                    #~ level=logging.DEBUG,
                    #~ #level = logging.ERROR,
                    #~ )
    global TOR_PORTS
    if len(argv) > 1 and argv[1].isdigit():
        TOR_PORTS = (int(argv[1]),)
    Controller(portlist=TOR_PORTS).run()



class Controller(object):

    def output(self, text):
        self.output_w.append_text('{}\n'.format(text))

    def __init__(self, portlist):
        self.root = None  # Main Tk window
        self.output_w = None  # Text output widget
        self.treeview = None

        self._init_ui()
        self.torlink_obj = TorLink(controller=self, portlist=portlist)

    def _init_ui(self):
        # --- Tk init ---
        self.root = root = tk.Tk()
        root.title('OnionView')
        #~ root.geometry('1000x1000')

        # Catch the close button
        root.protocol("WM_DELETE_WINDOW", self.cmd_quit)
        # Catch the "quit" event.
        #root.createcommand('exit', self.cmd_quit)

        root.option_add('*tearOff', False)
        root.bind('<Alt_L><q>', self.cmd_quit)

        # --- Main TreeView ---

        #Style().configure('TFrame', background='black', foreground='green')
        treeframe = ttk.Frame(root)#, borderwidth=10, relief='ridge')
        self.treeview = TreeView(treeframe, controller=self)
        treeframe.grid(row=20, column=0, columnspan=2, sticky='nsew')

        root.columnconfigure(0, weight=1)
        root.rowconfigure(20, weight=3)

        # --- Output Widget ---

        outputframe = ttk.Frame(root)#, borderwidth=10, relief='ridge')
        outputframe.grid(row=30, column=0, columnspan=2, sticky='nsew')
        self.output_w = OutputW(outputframe, self)

        # --- Statusbar ---

        self.status = tk.StringVar()
        #self.status.set('Processing...')
        status = ttk.Label(root, textvariable=self.status,
                       relief=tk.SUNKEN, anchor=tk.W)
        status.grid(row=40, column=0, sticky='wse')

        grip = ttk.Sizegrip(root)
        grip.grid(row=40, column=1, sticky=tk.SE)

    def cmd_quit(self, *ign):
        logd('cmd_quit called')
        self.root.quit()

    def run(self):
        self.root.mainloop()  # Run the Tk GUI

    def set_current_id(self, sid):
        self.current_id = sid
        self.current_id_var.set('Current Identity: {}'.format(sid))

    def show_circuit(self, circuit):
        self.treeview.show_circuit(circuit)

    def show_stream(self, stream):
        self.treeview.show_stream(stream)



class OutputW(object):
    '''Draws and controls the Output Widget'''
    def __init__(self, parent, controller):
        self.controller = controller
        self.parent = parent
        self.frame = ttk.Frame(parent)#, borderwidth=10, relief='ridge')#, padding=10
        self.frame.pack(fill=tk.BOTH)

        self.output_w = tk.Text(self.frame, width=120, height=15)
        self.output_w.grid(row=0, column=0, sticky=tk.NSEW)
        #~ self.output_w.insert('1.0', 'Output will appear here.')

        scroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL,
                               command=self.output_w.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.output_w.configure(yscrollcommand=scroll.set)
        self.yscroll = scroll

    def append_text(self, text):
        '''Append text to the contents of the output window'''
        self.output_w.insert('end', text)
        self.output_w.see('end')

    def replace_text(self, text):
        '''Replace the contents of the output window with supplied text'''
        self.output_w.delete('1.0', 'end')
        self.output_w.insert('1.0', text)



class TorLink(object):
    def __init__(self, controller, portlist=TOR_PORTS):
        self.controller = controller
        self.treeview = controller.treeview
        self.tor = None
        self.circuits = {}
        self.streams = defaultdict(dict)

        # Initialise the link to Tor
        for port in portlist:
            try:
                #print('Trying port ', port)
                tor = stem.control.Controller.from_port(port=port)
                tor.authenticate()
                print('Connected to Tor on port:%s' % port)
                self.tor = tor
                self.port = port
                break
            except stem.SocketError:
                #print('stem.SocketError')
                pass
        else:
            sys.exit('Unable to contact Tor process')

        # Set up callbacks for the events we want
        EventType = stem.control.EventType
        #tor.add_event_listener(self.handle_bw_event, EventType.BW)
        #~ tor.add_event_listener(self.handle_event,
            #~ EventType.ADDRMAP,
            #~ )
        tor.add_event_listener(self.handle_stream_event,
            EventType.STREAM,
            )
        tor.add_event_listener(self.handle_circuit_event,
            EventType.CIRC,
            #EventType.CIRC_MINOR,
            )

        # List the existing circuits and streams
        for circuit in sorted(tor.get_circuits(), key=lambda circuit: int(circuit.id)):
            controller.show_circuit(self._enhance_circuit(circuit))
            #self.controller.output(circuit)
        for stream in sorted(tor.get_streams(), key=lambda stream: int(stream.id)):
            controller.show_stream(stream.__dict__)

    def handle_event(self, event):
        #print(dir(event))
        arrived_at = datetime.fromtimestamp(event.arrived_at).time()
        self.controller.output('_event {} {}'.format(arrived_at, event))

    def handle_bw_event(self, event):
        if event.read or event.written:
            self.controller.output('sent: %i, received: %i' % (event.written, event.read))

    def handle_circuit_event(self, event):
        try:
            self.controller.output('circ_event '+ str(event))
            self.controller.show_circuit(self._enhance_circuit(event))
        except Exception as e:
            print('Circuit event error:')
            print(e)
            print(event.__dict__)

    def handle_stream_event(self, event):
        try:
            #print('Stream event: %s' % event)
            self.controller.output(str(event))
            if event.status == 'NEW' or event.status == 'SENTRESOLVE':
                # Save dns name for later
                self.streams[event.id]['orig_target'] = event.target_address
            if event.circ_id is None:
                pass
            else:
                eventd = event.__dict__.copy()
                # Add our saved data
                eventd.update(self.streams[event.id])
                self.controller.show_stream(eventd)
        except Exception as e:
            print('Stream event error:')
            print(e)
            print(event.__dict__)

    def _enhance_circuit(self, circuit):
        # Add additional information to a circuit
        pathplus = []
        for relay_fp, relay_nick in circuit.path:
            #print('Relay:', relay_fp)
            relay_status = self.tor.get_network_status(relay_fp)
            #print('Status:\n%s' % (relay_status.__dict__))
            #relay_descriptor = self.tor.get_microdescriptor(relay_fp)
            #print('Descriptor:\n%s' % (relay_descriptor.__dict__))
            country = self.tor.get_info('ip-to-country/%s' % relay_status.address)
            #print('Where:', country)
            pathplus.append((relay_fp, relay_nick, relay_status.address,
                country.upper()))
        circuit.pathplus = pathplus
        return circuit


class TreeView(object):
    '''Manages the TreeView'''
    def __init__(self, parent, controller):
        self.controller = controller

        #columns = ('id', 'Created', 'Path')
        self.tree_w = ttk.Treeview(parent, height=30)#,columns=columns)#, show='headings')
        self.tree_w.column('#0', stretch=True)#, width=900
        self.tree_w.tag_configure('closed', foreground='grey')
        #print(self.tree_w['columns'])
        #for column in self.tree_w['columns']:
        #    self.tree_w.column(column, minwidth=20, width=20, stretch=True)

        self.tree_w.grid(row=0, column=0, sticky=tk.NSEW)

        s = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree_w.yview)
        s.grid(row=0, column=1, sticky=tk.NS)
        self.tree_w.configure(yscrollcommand=s.set)
        self.yscroll = s

        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        self.tree_w.bind('<<TreeviewSelect>>', self.cmd_select)

    def cmd_select(self, event):
        '''Figures out which item was clicked and invokes relevant
        functionality.'''
        itemid = self.tree_w.focus()
        self.controller.output(itemid)
        #~ if itemid.startswith('peers.'):
            #~ sid = itemid[6:]
            #~ self.controller.peer_tab_obj.switch_to_sid(sid)

    def show_circuit(self, circuit, position='end'):
        '''Show a circuit in the treeview'''
        #print('show_circuit #{} Type{}'.format(circuit.id, type(circuit)))

        disp = '{0.id} {0.created} {0.status}: '.format(circuit)
        pathbits = []
        for relay in circuit.pathplus:
            # relay = (fp, name, addr, country)
            pathbits.append('{3} {1}'.format(*relay))
        disp += ' > '.join(pathbits)
        kwargs = circuit.keyword_args
        try:
            disp += ' : {}:{}'.format(
                kwargs['SOCKS_USERNAME'], kwargs['SOCKS_PASSWORD'])
        except KeyError as e:
            pass
            #print('raw_content:{!r}'.format(circuit.raw_content))
            #print(dir(circuit))
            #print(circuit.positional_args)
            #print(circuit.keyword_args)
        try:
            disp += ' : {}'.format(kwargs['BUILD_FLAGS'])
        except KeyError:
            pass
        item_id = 'circ.%s' % circuit.id

        if self.tree_w.exists(item_id):
            self.tree_w.item(item_id, text=disp)
            if circuit.status == 'CLOSED':
                self.tree_w.item(item_id, tags=('closed'))
        else:
            id = self.tree_w.insert('', position, item_id, text=disp, open=True)
            #if self.yscroll.get()[1] == 1.0:  # Scrollbar at bottom
            self.tree_w.see(id)  # Scroll to make it visible
        #self.controller.ttree.item(sid)['tags'] = 'disabled'

    def show_stream(self, stream):
        '''Show a stream in the treeview'''
        #print('stream show', self.yscroll.get())
        stream['orig_target'] = stream.get('orig_target', stream['target_address'])
        disp = '{id:>3} {status} {orig_target}({target_address}):{target_port}'.format(**stream)
        item_id = 'stream.%s' % stream['id']

        if self.tree_w.exists(item_id):
            self.tree_w.item(item_id, text=disp)
            if stream['status'] == 'CLOSED':
                self.tree_w.item(item_id, tags=('closed'))
        else:
            id = self.tree_w.insert('circ.%s' % stream['circ_id'], 'end',
                item_id, text=disp, )
            self.tree_w.see(id)  # Scroll to make it visible



# Functions ----------------------------------------------------------
#
logd = _logger.debug
logi = _logger.info
logw = _logger.warning  # Default log output level
loge = _logger.error
logc = _logger.critical


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and \
        (sys.argv[1] == '-h' or sys.argv[1] == '--help'):
        print(__doc__)
    else:
        main(sys.argv)

# Useful snippets:
# , borderwidth=10, relief='ridge'
# .pack(fill=tk.BOTH)
# logd('configure:%s', .configure())
