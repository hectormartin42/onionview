OnionView: Observe the circuits and streams of Tor.
======================================================

Version: 0.0.1  September 2016

Introduction
-------------

OnionView displays the circuits and streams which [Tor][1] creates to
service requests.

The display is a Graphical User Interface (GUI) using the Python Tk library
and shows each circuit as it is created and each stream using that circuit.
The excellent [Stem library][2] is used to interface with the running Tor
process via the Control Port.

All feedback, advice, constructive criticism and code contributions
gratefully received.

[1]: https://www.torproject.org/
[2]: https://stem.torproject.org/

Contact
--------

Code : <https://github.com/skyguy/onionview>

Email me at <onionview@kevinsteen.net>


Usage
------

1.  Ensure you have the `stem` library installed.

    On Debian you can install it by running
        `apt-get install python-stem`

2.  Ensure the Tor instance you want to monitor has a ControlPort configured.

3.  Copy the file `onionview.py` on to your system and run it. It will
    attempt to connect to a Tor Control Port on port 9153, then 9151, then 9051.


License
--------

Copyright 2016 Kevin Steen <ks@kevinsteen.net>

Unless otherwise indicated, all source code is Free Software. You can
redistribute it and/or modify it under the terms of the GNU Affero
General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.
A copy of the license can be found in the file `COPYING`.

---

This file is licensed under the Creative Commons Attribution-ShareAlike
4.0 International License. To view a copy of this license, visit
<http://creativecommons.org/licenses/by-sa/4.0/>
