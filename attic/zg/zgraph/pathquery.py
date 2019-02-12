from zgraph import *
from pprint import pprint
from UserList import UserList



class Paths(object):
    def __init__(self, pathlist=None, previous=None):
        pathlisttype = type(pathlist)
        # print pathlisttype
        if pathlisttype == Path:
            pathlist = Pathlist([pathlist])
        elif pathlisttype == Pathlist:
            pass
        else:
            pathlist = listify(pathlist)
            pathlist = Pathlist([Path([p]) for p in pathlist])
        self.pathlist = pathlist
        # print 's', self.pathlist
        self.previous = previous
        if self.previous is None:
            self.pathcounter = 0
        else:
            self.pathcounter = self.previous.pathcounter + 1
        self.result = []

    def __getattr__(self, key):
        out = Pathlist()
        for path in self.pathlist:
            ending = path[-1]
            if hasattr(ending, key):
                # print type(path)
                newpath = Path(path)
                newpath.values = dict(dict(getattr(Path, 'values', {})))
                newpath.append(getattr(ending, key))
                out.append(newpath)
        return Paths(out, self)

    def __call__(self, *args, **kwargs):
        out = Pathlist()
        # print self.pathlist
        for path in self.pathlist:
            ending = path[-1]
            val = ending(*args, **kwargs)
            if type(val) in (tuple, list, OIBTree.OITreeSet):
                for v in val:
                    # print type(path)
                    newpath = Path(path)
                    newpath.values = dict(getattr(Path, 'values', {}))
                    newpath.pop()
                    # print type(newpath)
                    newpath.append(v)
                    out.append(newpath)
            else:
                path.append(val)
                out.append(path)
        return Paths(out, self)

    def paths(self):
        return self.pathlist

    def v(self, *args):
        for path in self.pathlist:
            # print path
            if not hasattr(path, 'values'):
                path.values = {}
            if len(args) == 1:
                path.values[args[0]] = path[-1]
            else:
                path.values[args[1]] = getattr(path[-1], args[0])

        return self

    def repeat(self, min, max):
        return self

    def filter(self, spec):
        return self

    @property
    def values(self):
        out = []
        for path in self.pathlist:
            out.append(path.values)
        return out


class Results(object):
    pass


class Pathlist(UserList):
    def __init__(self, iterable=None):
        super(Pathlist, self).__init__(iterable)

    def __repr__(self):
        return '<Pathlist([%s]) at %s>' % (','.join([str(i) for i in self]), str(id(self))[-5:])


class Path(UserList):
    def __init__(self, iterable=None):
        super(Path, self).__init__(iterable)

    def __repr__(self):
        return '<Path([%s]) at %s>' % (','.join([str(i) for i in self]), str(id(self))[-5:])


if __name__ == '__main__':

    zg = ZGraph('zdata')
    apple = zg.nodecatalog.q('name=="Apple"')[0]
    print apple

    paths = Paths(apple).incoming('creates').source.v('creator').outgoing('creates').target.v('creation')
    for p in paths.pathlist:
        print id(p), p.values
    print
    paths = Paths(apple).incoming().source.v('hop1').outgoing().target.v('hop2')
    for p in paths.pathlist:
        print p, p.values

        # 140390837227952 {'creation': <Node(['Human', 'Female'], _id=6)>}
        # 140390837228040 {'creation': <Node(['Human', 'Male'], _id=5)>}
        # 140390837228128 {'creation': <Node(['Snake', 'Animal'], _id=4)>}
        # 140390837228216 {'creation': <Node(['Apple', 'Plant', 'Fruit'], _id=3)>}
        # 140390837228304 {'creation': <Node(['Tree', 'Plant'], _id=2)>}
