import argparse
import os
import ZODB
import time
import sys
from ZODB.FileStorage import FileStorage
from ZODB import MappingStorage
from ZODB import blob
import persistent
from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from BTrees import IOBTree, OOBTree, OIBTree
import re
import transaction
from hashlib import md5
from ZEO import ClientStorage
from BTrees.Length import Length
from repoze.catalog.catalog import Catalog as RepozeCatalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from repoze.catalog.indexes.path import CatalogPathIndex
from repoze.catalog import query


class ResultSet(object):
    def __init__(self, start=None, previous=None, values=None):
        self.start = listify(start)
        self.previous = previous

        if values is not None:
            self.values = values
        elif self.previous is not None:
            self.values = previous.values
        else:
            self.values = {}

    def __getattr__(self, key):
        # print self.start
        out = []
        for element in self.start:
            a = getattr(element, key)
            out.append(a)
        return ResultSet(out, self)

    def __call__(self, *args, **kwargs):
        out = []
        for element in self.start:
            val = element(*args, **kwargs)
            if type(val) in (tuple, list, OIBTree.OITreeSet):
                out.extend(val)
            else:
                out.append(val)
        return ResultSet(out, self)

    def __getitem__(self, key):
        return self.values[key]

    def _as(self, *args):
        if len(args) == 1:
            self.values[args[0]] = self.start
        else:
            self.values[args[1]] = [getattr(e, args[0]) for e in self.start]

        return self

    @property
    def v(self):
        return self.start

    @property
    def kept(self):
        return ResultSet(self.values, self)


class PObject(Persistent):
    pass


def listify(obj):
    if obj is None:
        return []
    elif type(obj) not in (tuple, list):
        return [obj]
    else:
        return obj


class Labeled(Persistent):
    def getKeys(self):
        return [k for k in dir(self) if not (k.startswith('_') or callable(getattr(self, k)))]

    def getItems(self):
        return [(k, getattr(self, k)) for k in self.getKeys()]

    def p(self, key, default=None):
        return getattr(self, key, default)


class Node(Labeled):
    def __init__(self, labels=None, _id=None, **kwargs):
        self._id = _id
        labels = listify(labels)
        self._labels = labels
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._incoming = OIBTree.OITreeSet()  # incoming edges
        self._outgoing = OIBTree.OITreeSet()  # outgoing edges

    def __repr__(self):
        return " N%s:%s" % (self._id, ':'.join(self.labels))

    @property
    def labels(self):
        return self._labels

    # @property
    def incoming(self, label=None):
        if label is None:
            return self._incoming
        else:
            return [e for e in self._incoming if label == e.label]

    # @property
    def outgoing(self, label=None):
        if label is None:
            return self._outgoing
        else:
            return [e for e in self._outgoing if label == e.label]


class Edge(Labeled):
    def __init__(self, source, label, target, _id=None, **kwargs):
        self._id = _id
        self._label = label
        for k, v in kwargs.items():
            setattr(self, k, v)

        self._source = source
        source._outgoing.add(self)
        source._p_changed = True

        self._target = target
        target._incoming.add(self)
        target._p_changed = True

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    @property
    def label(self):
        return self._label

    def __repr__(self):
        return " E%s %s %s %s" % (self._id,
                                  self.source._id,
                                  self.label,
                                  self.target._id)

    def __cmp__(self, other):
        return cmp(self._id, other._id)


class Catalog(RepozeCatalog):
    def __init__(self, family=None, object_store=None):
        super(Catalog, self).__init__(family)
        self.object_store = object_store

    _targetypes = dict(field=CatalogFieldIndex,
                       text=CatalogTextIndex,
                       path=CatalogPathIndex,
                       keyword=CatalogKeywordIndex)

    def addIndex(self, name, type, getterclass=None):
        if name in self:
            return self[name]
        if getterclass is None:
            getterclass = ValueGetter
        getter = getterclass(name)
        idx = self._targetypes[type](getter)
        self[name] = idx
        return idx

    def q(self, *args, **kwargs):
        result = self.query(*args, **kwargs)
        return [self.object_store[i] for i in result[1]]


class Getter(object):
    def __init__(self, key):
        self.key = key


class RawGetter(Getter):
    def __call__(self, obj, default):
        out = []
        for data in obj.raw:
            if data[0] == self.key:
                out.append(data[1])
        if out:
            return out
        else:
            return default


class ValueGetter(Getter):
    def __call__(self, obj, default):
        val = getattr(obj, self.key, default)
        # print 'ValueGetter %s for %s: %s ' % (self.key, obj, val)
        return val


class IndexOnly(Getter):
    def __call__(self, obj, default):

        if hasattr(obj, self.key):
            val = getattr(obj, self.key)
            setattr(obj, self.key, None)
        else:
            val = default
        # print 'indexonly', obj, val
        return val


class ZGraph(object):
    def __init__(self, directory=None, server=None):
        self.directory = directory
        if directory:
            if not os.path.isdir(directory):
                os.mkdir(directory)
            blobdir = os.path.join(directory, 'blobstorage')
            if not os.path.isdir(blobdir):
                os.mkdir(blobdir)
            storage = FileStorage(os.path.join(directory, 'zgraph.db'),
                                  blob_dir=blobdir)
        elif server:
            storage = ClientStorage.ClientStorage(server)
        else:
            raise Exception("Can't create storage")

        self.storage = storage
        self.db = ZODB.DB(self.storage, large_record_size=16777216 * 2)
        self.connection = self.db.open()
        self.root = self.connection.root

        if not getattr(self.root, '_initialized', False):
            print 'Initializing ZGraph in', self.directory
            self.root.nodes = IOBTree.IOBTree()
            self.root.edges = IOBTree.IOBTree()
            self.root._edgeid = Length()
            self.root._nodeid = Length()
            self.root.nodecatalog = Catalog(object_store=self.root.nodes)
            self.root.edgecatalog = Catalog(object_store=self.root.edges)
            self.root._initialized = True

        if not hasattr(self.root, 'typeids'):
            print 'adding Graphagus'
            self.addGraphagus()

        self.nodes = self.root.nodes
        self.edges = self.root.edges
        self._edgeid = self.root._edgeid
        self._nodeid = self.root._nodeid
        self.nodecatalog = self.root.nodecatalog
        self.edgecatalog = self.root.edgecatalog

        self.outbytype = self.root.outbytype
        self.inbytype = self.root.inbytype
        self.outbysource = self.root.outbysource
        self.inbytarget = self.root.inbytarget

        self._typeid = self.root._typeid
        self.typeids = self.root.typeids
        self.revtypes = self.root.revtypes

    def commit(self):
        transaction.commit()

    def savepoint(self):
        transaction.savepoint()

    def close(self):
        self.db.close()

    def pack(self, t=None, days=0):
        return self.db.pack(t, days)

    def nodeid(self):
        self._nodeid.change(1)
        return self._nodeid.value

    def addGraphagus(self):
        self.root._typeid = Length()
        self.root.typeids = OIBTree.OIBTree()
        self.root.revtypes = IOBTree.IOBTree()
        self.root.outbytype = IOBTree.IOBTree()
        self.root.inbytype = IOBTree.IOBTree()
        self.root.outbysource = IOBTree.IOBTree()
        self.root.inbytarget = IOBTree.IOBTree()

    def typeid(self, name):
        if not self.typeids.has_key(name):
            self._typeid.change(1)
            tid = self._typeid.value
            self.typeids[name] = tid
            self.revtypes[tid] = name
        return self.typeids[name]

    def edgeid(self):
        self._edgeid.change(1)
        return self._edgeid.value

    def addNode(self, node):
        if node._id is None:
            node._id = self.nodeid()
        self.nodes[node._id] = node
        self.nodecatalog.index_doc(node._id, node)
        return node

    def addEdge(self, edge):
        if edge._id is None:
            edge._id = self.edgeid()
        self.edges[edge._id] = edge

        self.addEdgeToGraphagus(edge)

        self.edgecatalog.index_doc(edge._id, edge)
        return edge

    def addEdgeToGraphagus(self, edge):

        sourceid = edge.source._id
        targetid = edge.target._id
        typeid = self.typeid(edge.label)

        data = self.outbytype.setdefault(typeid, IOBTree.IOBTree()).setdefault(sourceid, {})
        data[edge._id] = targetid
        self.outbytype[typeid][sourceid] = data

        data = self.inbytype.setdefault(typeid, IOBTree.IOBTree()).setdefault(targetid, {})
        data[edge._id] = sourceid
        self.inbytype[typeid][targetid] = data

        data = self.outbysource.setdefault(sourceid, IOBTree.IOBTree()).setdefault(typeid, {})
        data[edge._id] = targetid
        self.outbysource[sourceid][typeid] = data

        data = self.inbytarget.setdefault(targetid, IOBTree.IOBTree()).setdefault(typeid, {})
        data[edge._id] = sourceid
        self.inbytarget[targetid][typeid] = data


if __name__ == '__main__':

    zg = ZGraph('zdata')
    if 1:
        zg.nodecatalog.addIndex('name', 'field')
        zg.nodecatalog.addIndex('text', 'text', IndexOnly)

        jehova = zg.addNode(Node('God', name='Jehova', text='let it be light '))
        tree = zg.addNode(Node(['Tree', 'Plant'], name='Tree'))
        apple = zg.addNode(Node(['Apple', 'Plant', 'Fruit'], name='Apple'))
        snake = zg.addNode(Node(['Snake', 'Animal'], name='Snake', text='sss'))
        adam = zg.addNode(Node(['Human', 'Male'], name='Adam'))
        eve = zg.addNode(Node(['Human', 'Female'], name='Eve'))

        zg.addEdge(Edge(jehova, 'creates', tree))
        zg.addEdge(Edge(jehova, 'creates', apple))
        zg.addEdge(Edge(jehova, 'creates', snake))
        zg.addEdge(Edge(jehova, 'creates', adam))
        zg.addEdge(Edge(jehova, 'creates', eve))
        zg.addEdge(Edge(snake, 'talks', eve))
        zg.addEdge(Edge(eve, 'takes', apple))
        zg.addEdge(Edge(eve, 'gives', apple, to=adam))
    else:
        apple = zg.nodecatalog.q('name=="Apple"')[0]

    print zg.nodecatalog.query(query.Eq('name', 'Eve'))
    print
    print zg.nodecatalog.q(query.Eq('text', 'light'))
    print
    p = ResultSet(apple).incoming('takes').source._as('source').outgoing().target.name._as('name')
    print p.values

    # Initializing ZGraph
    # (ResultSetSize(1, 1), IFSet([6]))
    #
    # [ N1:God]
    #
    # [ N3:Apple:Plant:Fruit]
    # [ E7 6 takes 3]
    # [ N6:Human:Female]
    # [ E8 6 gives 3,  E7 6 takes 3]
    # [ N3:Apple:Plant:Fruit,  N3:Apple:Plant:Fruit]
    # {'source': [ N6:Human:Female], 'name': ['Apple', 'Apple']}

    # apple.incoming()
    # import ipdb; ipdb.set_trace()



    zg.commit()
    zg.pack()
    zg.close()
