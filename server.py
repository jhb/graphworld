import neo4j as neo4j
from chameleon import PageTemplate, PageTemplateLoader
from wtforms import Form, BooleanField, StringField, validators, widgets, SelectField
#from flask_wtf import FlaskForm as Form
import flask
from flask import request
from neo4j import GraphDatabase

api = flask.Flask(__name__)
api.secret_key = b'GraphIsGreat'

driver = GraphDatabase.driver('bolt://localhost:7687')


class DictObject:

    def __init__(self,items):
        self._items = items
        self.labels = []
        for k,v in items:
            setattr(self,k,v)

    def items(self):
        return self._items

class TemplateWrapper:

    def __init__(self,template,**kwargs):
        self.template=template
        self.kwargs=kwargs

    def __call__(self,**kwargs):
        kwargs.update(self.kwargs)
        return self.template(**kwargs)

def getTemplate(name):
    templates = PageTemplateLoader('templates', '.pt')
    return TemplateWrapper(templates[name],flask=flask,templates=templates)

def getSemProperties():
    with driver.session() as session:
        result = session.run('match (semprop:SemProperty) return semprop')
        sp = dict()
        for row in result:
            properties = dict(row['semprop'].items())
            sp[properties['shortname']]=properties
    return sp


def getNode(nid):
    with driver.session() as session:
        result = session.run("match (n) where id(n)={id} return n",id=nid)
        return result.single()['n']

def getNodes():
    with driver.session() as session:
        result = session.run('match (n) return n order by id(n)')
        return [row['n'] for row in result]

def updateNode(nid,items):
    itemsd = dict(items)
    t = "n.%s = '%s'"
    parts = []
    for k,v in items:
        if k.startswith('new_'):
            continue
        parts.append(t %(k,v))
    if itemsd['new_attribute']:
        parts.append(t % (itemsd['new_attribute'],itemsd['new_value']))
    statement = """MATCH (n) WHERE id(n) = %s SET %s""" % (nid,', '.join(parts))
    with driver.session() as session:
        result = session.run(statement)
    return statement

def delNodeProperty(nid,propertyname):
    statement = """MATCH (n) WHERE id(n) = %s REMOVE n.%s""" % (nid,propertyname)
    with driver.session() as session:
        result = session.run(statement)

class Schema():

    def __init__(self,resultrow):
        self.n = resultrow['n']
        self.props = list(resultrow['props'])
        self.propnames = set([p['shortname'] for p in self.props])

    def match(self,node):
        if self.propnames.issubset(node.keys()):
            return True


def getSchemas():
    statement = "match (n:SemLabel)-[:SEMPROP]->(p:SemProperty) return n,collect(p) as props;"
    with driver.session() as session:
        result = session.run(statement)
    return [Schema(row) for row in result]

@api.route('/nodelist')
def nodelist():
    nodes = getNodes()
    template = getTemplate('nodelist.pt')
    return template(nodes=nodes)



@api.route('/node/<nid>', methods=['POST', 'GET'])
def node(nid=7):

    if 'delete' in request.args:
        delNodeProperty(nid,request.args['delete'])
        flask.flash('%s removed from node' % request.args['delete'])
        return flask.redirect(request.base_url)

    if nid!='new':
        node = getNode(int(nid))
    else:
        node = DictObject([])

    # if request.method=='GET':

    # build the form
    class MyForm(Form):
        pass



    if request.method=='POST':
        items = request.form.items()
    else:
        items = node.items()

    items = list(items)
    itemsd = dict(items)
    sproperties = getSemProperties()
    for k,v in sorted(items):
        if k.startswith('new_'):
            continue
        scalartype = sproperties[k]['scalartype']

        if scalartype == 'string':
            setattr(MyForm,k,StringField(k,description=sproperties[k].get('description','no description')))

    #setattr(MyForm,'newvalue',StringField('newvalue'))
    choices = [('','Select new attribute')]
    print(items)
    for k,v in sproperties.items():
        if k not in itemsd:
            choices.append((k,'%s - %s' % (k,v['description'])))
    MyForm.new_attribute=SelectField('New Attribute', description='A new attribute for this object', choices=choices)
    MyForm.new_value=StringField('New Value',description='The value of the new property')

    form = MyForm(request.form,DictObject(items))
    if request.method=='POST' and form.validate():
        statement = updateNode(nid,items)
        flask.flash('Node %s updated <small> -- %s</small>' % (nid,statement))
        return flask.redirect('/nodelist#%s' % nid)
    template = getTemplate('nodeform.pt')

    schemas = getSchemas()
    return template(form=form,node=node,sproperties=sproperties,schemas=schemas)

if __name__ == '__main__':
    print('x'*30)
    api.run(debug=1,port=9000)


#-b 0.0.0.0:9000 --reload --access-logfile - --error-logfile - -t 0 server:api