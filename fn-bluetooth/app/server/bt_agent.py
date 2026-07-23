# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import dbus  # pyright: ignore[reportMissingImports]
import dbus.service  # pyright: ignore[reportMissingImports]
import dbus.mainloop.glib  # pyright: ignore[reportMissingImports]
from gi.repository import GLib  # pyright: ignore[reportMissingImports]
import sys
import os
import time

AGENT_PATH = "/org/bluez/auto_agent"
OBEX_AGENT_PATH = "/org/bluez/obex/auto_agent"
BUS_NAME = "org.bluez"
OBEX_BUS_NAME = "org.bluez.obex"
AGENT_IFACE = "org.bluez.Agent1"
OBEX_AGENT_IFACE = "org.bluez.obex.Agent1"


class AutoAgent(dbus.service.Object):
    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        print("Agent: Release called", flush=True)

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print(
            f"Agent: AuthorizeService device={device} uuid={uuid} -> AUTO YES",
            flush=True,
        )

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print(f"Agent: RequestPinCode device={device} -> 0000", flush=True)
        return "0000"

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print(f"Agent: RequestPasskey device={device} -> 0", flush=True)
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def DisplayPasskey(self, device, passkey):
        print(f"Agent: DisplayPasskey device={device} passkey={passkey}", flush=True)

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print(f"Agent: DisplayPinCode device={device} pincode={pincode}", flush=True)

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print(
            f"Agent: RequestConfirmation device={device} passkey={passkey} -> AUTO YES",
            flush=True,
        )

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print(f"Agent: RequestAuthorization device={device} -> AUTO YES", flush=True)

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("Agent: Cancel called", flush=True)


class ObexAutoAgent(dbus.service.Object):
    def __init__(self, bus, path):
        super().__init__(bus, path)
        self._bus = bus

    @dbus.service.method(OBEX_AGENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        print("OBEX Agent: Release called", flush=True)

    @dbus.service.method(OBEX_AGENT_IFACE, in_signature="o", out_signature="s")
    def AuthorizePush(self, transfer_path):
        try:
            transfer_obj = self._bus.get_object(OBEX_BUS_NAME, transfer_path)
            props = dbus.Interface(transfer_obj, "org.freedesktop.DBus.Properties")
            name = str(props.Get("org.bluez.obex.Transfer1", "Name"))
            size = int(props.Get("org.bluez.obex.Transfer1", "Size"))
            print(
                f"OBEX Agent: AuthorizePush {transfer_path} name={name} size={size} -> ACCEPT",
                flush=True,
            )
        except Exception as e:
            print(
                f"OBEX Agent: AuthorizePush {transfer_path} -> ACCEPT ({e})", flush=True
            )
        return ""

    @dbus.service.method(OBEX_AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("OBEX Agent: Cancel called", flush=True)


def _setup_session_env():
    xdg = f"/run/user/{os.getuid()}"  # pyright: ignore[reportAttributeAccessIssue]
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={xdg}/bus"
    os.environ["XDG_RUNTIME_DIR"] = xdg


def _wait_for_obexd(max_wait=15):
    bus_addr = os.environ.get(
        "DBUS_SESSION_BUS_ADDRESS",
        f"unix:path=/run/user/{os.getuid()}/bus",  # pyright: ignore[reportAttributeAccessIssue]
    )
    for i in range(max_wait * 2):
        try:
            bus = dbus.bus.BusConnection(bus_addr)
            bus.get_object(OBEX_BUS_NAME, "/org/bluez/obex")
            bus.close()
            return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _register_obex_agent(session_bus):
    try:
        obex_agent = ObexAutoAgent(session_bus, OBEX_AGENT_PATH)
        obex_mgr = dbus.Interface(
            session_bus.get_object(OBEX_BUS_NAME, "/org/bluez/obex"),
            "org.bluez.obex.AgentManager1",
        )
        obex_mgr.RegisterAgent(OBEX_AGENT_PATH)
        print("OBEX Agent registered (auto-accept all pushes)", flush=True)
        return True
    except Exception as e:
        print(f"OBEX Agent registration failed: {e}", flush=True)
        return False


def main():
    _setup_session_env()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    system_bus = dbus.SystemBus()
    agent = AutoAgent(system_bus, AGENT_PATH)
    try:
        mgr = dbus.Interface(
            system_bus.get_object(BUS_NAME, "/org/bluez"), "org.bluez.AgentManager1"
        )
        mgr.RegisterAgent(AGENT_PATH, "DisplayYesNo")
        mgr.RequestDefaultAgent(AGENT_PATH)
        print("BlueZ Agent registered as DisplayYesNo", flush=True)
    except Exception as e:
        print(f"BlueZ Agent registration failed: {e}", flush=True)
        print("Retrying in 3 seconds...", flush=True)
        for retry in range(5):
            time.sleep(3)
            try:
                mgr = dbus.Interface(
                    system_bus.get_object(BUS_NAME, "/org/bluez"),
                    "org.bluez.AgentManager1",
                )
                mgr.RegisterAgent(AGENT_PATH, "DisplayYesNo")
                mgr.RequestDefaultAgent(AGENT_PATH)
                print("BlueZ Agent registered on retry", flush=True)
                break
            except Exception as e2:
                print(f"BlueZ Agent retry {retry + 1} failed: {e2}", flush=True)

    bus_addr = os.environ.get(
        "DBUS_SESSION_BUS_ADDRESS",
        f"unix:path=/run/user/{os.getuid()}/bus",  # pyright: ignore[reportAttributeAccessIssue]
    )
    obex_registered = False
    session_bus = None

    for attempt in range(10):
        try:
            session_bus = dbus.bus.BusConnection(bus_addr)
            session_bus.get_object(OBEX_BUS_NAME, "/org/bluez/obex")
            if _register_obex_agent(session_bus):
                obex_registered = True
                break
        except Exception as e:
            print(
                f"OBEX session bus connect attempt {attempt + 1}/10 failed: {e}",
                flush=True,
            )
            if session_bus:
                try:
                    session_bus.close()
                except Exception:
                    pass
                session_bus = None
        if attempt == 0:
            print("Waiting for obexd to be ready...", flush=True)
            _wait_for_obexd()
        else:
            time.sleep(2)

    if not obex_registered:
        print("WARNING: OBEX Agent registration failed after 10 attempts", flush=True)
        print("Incoming file transfers will be rejected (0x43 Forbidden)", flush=True)
        print("Possible causes:", flush=True)
        print("  1. obexd not running with -a flag", flush=True)
        print(f"  2. D-Bus session bus not available at {bus_addr}", flush=True)
        print("  3. obexd not registered on session bus", flush=True)

    if session_bus:

        def _on_name_owner_changed(name, old_owner, new_owner):
            if name == OBEX_BUS_NAME and new_owner != "":
                print(
                    f"obexd appeared on bus, re-registering OBEX Agent...", flush=True
                )
                GLib.timeout_add_seconds(
                    2, lambda: _register_obex_agent(session_bus) and False
                )

        try:
            session_bus.add_signal_receiver(
                _on_name_owner_changed,
                signal_name="NameOwnerChanged",
                dbus_interface="org.freedesktop.DBus",
            )
        except Exception as e:
            print(f"Could not watch for obexd restarts: {e}", flush=True)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
