# Copyright 2022-2023 Free Software Foundation, Inc.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gdb

from .frames import frame_for_id
from .startup import send_gdb_with_response, in_gdb_thread
from .server import request
from .varref import BaseReference


# Map DAP frame IDs to scopes.  This ensures that scopes are re-used.
frame_to_scope = {}


# When the inferior is re-started, we erase all scope references.  See
# the section "Lifetime of Objects References" in the spec.
@in_gdb_thread
def clear_scopes(event):
    global frame_to_scope
    frame_to_scope = {}


gdb.events.cont.connect(clear_scopes)


class _ScopeReference(BaseReference):
    def __init__(self, name, hint, frame, var_list):
        super().__init__(name)
        self.hint = hint
        self.frame = frame
        self.inf_frame = frame.inferior_frame()
        self.func = frame.function()
        self.line = frame.line()
        # VAR_LIST might be any kind of iterator, but it's convenient
        # here if it is just a collection.
        self.var_list = tuple(var_list)

    def to_object(self):
        result = super().to_object()
        result["presentationHint"] = self.hint
        # How would we know?
        result["expensive"] = False
        result["namedVariables"] = len(self.var_list)
        if self.line is not None:
            result["line"] = self.line
            # FIXME construct a Source object
        return result

    def has_children(self):
        return True

    def child_count(self):
        return len(self.var_list)

    @in_gdb_thread
    def fetch_one_child(self, idx):
        # Make sure to select the frame first.  Ideally this would not
        # be needed, but this is a way to set the current language
        # properly so that language-dependent APIs will work.
        self.inf_frame.select()
        # Here SYM will conform to the SymValueWrapper interface.
        sym = self.var_list[idx]
        name = str(sym.symbol())
        val = sym.value()
        if val is None:
            # No synthetic value, so must read the symbol value
            # ourselves.
            val = sym.symbol().value(self.inf_frame)
        elif not isinstance(val, gdb.Value):
            val = gdb.Value(val)
        return (name, val)


class _RegisterReference(_ScopeReference):
    def __init__(self, name, frame):
        super().__init__(
            name, "registers", frame, frame.inferior_frame().architecture().registers()
        )

    @in_gdb_thread
    def fetch_one_child(self, idx):
        return (
            self.var_list[idx].name,
            self.inf_frame.read_register(self.var_list[idx]),
        )


# Helper function to create a DAP scopes for a given frame ID.
@in_gdb_thread
def _get_scope(id):
    global frame_to_scope
    if id in frame_to_scope:
        scopes = frame_to_scope[id]
    else:
        frame = frame_for_id(id)
        scopes = []
        # Make sure to handle the None case as well as the empty
        # iterator case.
        args = tuple(frame.frame_args() or ())
        if args:
            scopes.append(_ScopeReference("Arguments", "arguments", frame, args))
        # Make sure to handle the None case as well as the empty
        # iterator case.
        locs = tuple(frame.frame_locals() or ())
        if locs:
            scopes.append(_ScopeReference("Locals", "locals", frame, locs))
        scopes.append(_RegisterReference("Registers", frame))
        frame_to_scope[id] = scopes
    return [x.to_object() for x in scopes]


@request("scopes")
def scopes(*, frameId: int, **extra):
    scopes = send_gdb_with_response(lambda: _get_scope(frameId))
    return {"scopes": scopes}
