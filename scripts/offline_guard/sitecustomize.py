"""Deny Python socket activity during the supplemental baseline verification."""
import sys

sys.dont_write_bytecode = True


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "socket.sendmsg", "socket.bind"}:
        raise RuntimeError("Network is forbidden during offline baseline verification")


sys.addaudithook(deny_network)
