"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

from pickle import TRUE
import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = True

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        # {(host, port): TableEntry(dst, port, latency, expire_time)}
        # record the latest route advertisement
        self.history = {}

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        # TODO: fill this in!
        latency = self.ports.get_latency(port)
        self.table[host] = TableEntry(host, port, latency, expire_time=FOREVER)

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        # TODO: fill this in!

        # If no route exists for a packet’s destination
        dest = packet.dst
        if dest not in self.table:
            return

        entry = self.table.get(dest)
        # if the latency is greater than or equal to INFINITY you should also drop the packet
        if entry.latency >= INFINITY:
            return

        if entry.port == in_port:
            return

        self.send(packet, entry.port)

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        # TODO: fill this in!
        # Send route advertisements for all routes
        for host, entry in self.table.items():
            if single_port != None:
                port_arr = [single_port]
            else:
                port_arr = self.ports.get_all_ports()

            for port in port_arr:
                next_hop = entry.port
                history_entry = self.history.get((port, host))

                if self.SPLIT_HORIZON:
                    if port != next_hop:
                        if force == False:
                            if history_entry == None or history_entry.dst != host or history_entry.latency != entry.latency:
                                self.send_route(port, host, entry.latency)
                                self.history[(port, host)] = TableEntry(
                                    host, port, entry.latency, entry.expire_time)
                        else:
                            self.send_route(port, host, entry.latency)
                            self.history[(port, host)] = TableEntry(
                                host, port, entry.latency, entry.expire_time)

                elif self.POISON_REVERSE:
                    if port == next_hop:
                        if force == False:
                            if history_entry == None or history_entry.dst != host or history_entry.latency != INFINITY:
                                self.send_route(port, host, INFINITY)
                                self.history[(port, host)] = TableEntry(
                                    host, port, INFINITY, entry.expire_time)
                        else:
                            self.send_route(port, host, INFINITY)
                            self.history[(port, host)] = TableEntry(
                                host, port, INFINITY, entry.expire_time)
                    else:
                        if force == False:
                            if history_entry == None or history_entry.dst != host or history_entry.latency != entry.latency:
                                self.send_route(port, host, entry.latency)
                                self.history[(port, host)] = TableEntry(
                                    host, port, entry.latency, entry.expire_time)
                        else:
                            self.send_route(port, host, entry.latency)
                            self.history[(port, host)] = TableEntry(
                                host, port, entry.latency, entry.expire_time)

                else:
                    if force == False:
                        if history_entry == None or history_entry.dst != host or history_entry.latency != entry.latency:
                            self.send_route(port, host, entry.latency)
                            self.history[(port, host)] = TableEntry(
                                host, port, entry.latency, entry.expire_time)
                    else:
                        self.send_route(port, host, entry.latency)
                        self.history[(port, host)] = TableEntry(
                            host, port, entry.latency, entry.expire_time)

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        # TODO: fill this in!
        for host in list(self.table.keys()):
            entry = self.table.get(host)

            # expired route poisoning
            if self.POISON_EXPIRED and entry.has_expired:
                poison_route = TableEntry(
                    host, entry.port, INFINITY, api.current_time() + self.ROUTE_TTL)
                self.table[host] = poison_route

            # if the route has expired
            elif entry.has_expired:
                del self.table[host]

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        # TODO: fill this in!
        cur_best_route = self.table.get(route_dst)

        link_latency = self.ports.get_latency(port)
        new_latency = link_latency + route_latency
        new_exp_time = api.current_time() + self.ROUTE_TTL
        new_route = TableEntry(route_dst, port, new_latency, new_exp_time)

        # if cur_best_route == None and route_latency < INFINITY: # if destination not in table - add to table
        if cur_best_route == None and route_latency < INFINITY:
            self.table[route_dst] = new_route

        else:
            next_hop = cur_best_route.port
            cur_latency = cur_best_route.latency

            # Ad from a poisoned entry
            if route_latency >= INFINITY and next_hop == port:
                poisoned_entry = TableEntry(
                    route_dst, port, INFINITY, cur_best_route.expire_time)
                self.table[route_dst] = poisoned_entry

            elif new_latency < cur_latency:  # if found a better route
                self.table[route_dst] = new_route

            elif new_latency == cur_latency:  # break tie to choose the current route
                self.table[route_dst] = cur_best_route

            elif next_hop == port:  # if the advertiser is current_next_hop
                self.table[route_dst] = new_route

        self.send_routes(False)

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        # TODO: fill in the rest!
        if self.SEND_ON_LINK_UP:
            self.send_routes(False, port)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        # TODO: fill this in!
        if self.POISON_ON_LINK_DOWN:
            for host in list(self.table.keys()):
                entry = self.table.get(host)
                next_hop = entry.port
                if port == next_hop:
                    poison_route = TableEntry(
                        host, port, INFINITY, api.current_time() + self.ROUTE_TTL)
                    self.table[host] = poison_route
            self.send_routes(False)

    # Feel free to add any helper methods!
