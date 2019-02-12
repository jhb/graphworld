from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.session import SignedCookieSessionFactory
from repoze.catalog.query import And, Eq, Contains
from collections import defaultdict
from pyramid.httpexceptions import HTTPFound

import os

import zgraph

class Nodelist(object):

    def __init__(self,nodeids=None,length=None,query=None):
        self.nodeids = nodeids
        self.length = length
        self.query = query

def queryText(zg,searchstring):
    print 'searching for', searchstring
    terms = searchstring.split()
    query = And(*[Contains('abstract', term) for term in terms])
    res = zg.nodecatalog.query(query, sort_index='abstract')
    return res

def queryOutgoing(zg,prevresult,typeids):
    nodeids = prevresult[1]
    targetids = set()
    for nodeid in nodeids:
        outgoing = zg.outbysource.get(nodeid,None)
        if outgoing is not None:
            for typeid in typeids:
                data = outgoing.get(typeid,None)
                if data is not None:
                    targetids.update(data.values())
    return (len(targetids),list(targetids))

def getOutgoing(zg,nodeids):
    print 'searching Outgoing of %s nodeids' % len(nodeids)
    linkcounter = dict()
    for nodeid in nodeids:
        outgoing = zg.outbysource.get(nodeid,dict())
        for typeid,data in outgoing.items():
            linkcounter[typeid] = linkcounter.get(typeid,0) +len(data)
    outlist = []
    for typeid,count in linkcounter.items():
        outlist.append((count,zg.revtypes[typeid],typeid))
    outlist.sort()
    outlist.reverse()
    return outlist

def queryIncoming(zg,prevresult,typeids):
    nodeids = prevresult[1]
    sourceids = set()
    for nodeid in nodeids:
        incoming = zg.inbytarget.get(nodeid,None)
        if incoming is not None:
            for typeid in typeids:
                data = incoming.get(typeid,None)
                if data is not None:
                    sourceids.update(data.values())
    return (len(sourceids),list(sourceids))

def getIncoming(zg,nodeids):
    print 'searching Incoming of %s nodeids' % len(nodeids)
    linkcounter = dict()
    for nodeid in nodeids:
        incoming = zg.inbytarget.get(nodeid,dict())
        for typeid,data in incoming.items():
            linkcounter[typeid] = linkcounter.get(typeid,0) +len(data)
    inlist = []
    for typeid,count in linkcounter.items():
        inlist.append((count,zg.revtypes[typeid],typeid))
    inlist.sort()
    inlist.reverse()
    return inlist

def serveSet(request):
    path = request.matchdict.get('path','/')
    params = request.params

    searchstring = params.get('searchstring', None)
    if searchstring:
        return HTTPFound(location='/text='+searchstring+'/')

    print 'Path:',path
    trail = []
    for pathelement in path:
        action,query = pathelement.split('=',1)
        trail.append((action,query))

    results = []
    displaytrail = []
    searchtext = ''
    for action,query in trail: #trail:
        print 'Action:', action, 'Query:', query
        if action=='text':
            result = queryText(zg,query)
            results.append(result)
            trailelement='text: "%s"' % query
            searchtext = query
        elif action=='out':
            result = queryOutgoing(zg,results[-1],[zg.typeids[query]])
            results.append(result)
            trailelement='outgoing: "%s"' % query.replace('dbpedia:', '').replace('_', ' ')
        elif action=='in':
            result = queryIncoming(zg,results[-1],[zg.typeids[query]])
            results.append(result)
            trailelement = 'incoming: "%s"' % query.replace('dbpedia:', '').replace('_', ' ')
        elif action=='nodeid':
            result = (1,[int(query)])
            results.append(result)
            trailelement = 'node: "%s" (%s)' % (zg.nodes[int(query)].title.replace('dbpedia:', '').replace('_', ' '), query)
        displaytrail.append(trailelement)
    if results:
        outgoing=getOutgoing(zg,results[-1][1])
        incoming=getIncoming(zg,results[-1][1])
    else:
        outgoing = []
        incoming = []
    out = dict(zg=zg,searchtext=searchtext,displaytrail=displaytrail,results=results,outgoing=outgoing,incoming=incoming,path=path)

    return out


print 'opening zgraph'
zg  = zgraph.ZGraph('graphdata')
#zg = zgraph.ZGraph(server=('localhost',9000))
#zg = zgraph.ZGraph(server='/home/joerg/tmp/zeosock')
print 'opened'
config = Configurator()
config.add_route('serveset', '/*path')
config.add_view(serveSet, route_name='serveset',renderer=os.getcwd()+'/zgserver.pt')
config.include('pyramid_chameleon')
my_session_factory = SignedCookieSessionFactory('mysecret')
config.set_session_factory(my_session_factory)
app = config.make_wsgi_app()

if __name__ == '__main__':
    server = make_server('0.0.0.0', 9999, app)
    server.serve_forever()
