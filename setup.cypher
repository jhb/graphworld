create (_0:`Person` {`firstname`:"Alice", `lastname`:"Alison", `name`:"Alice Alison"})
create (_1:`SemLabel` {`description`:"A human", `shortname`:"Person"})
create (_2:`SemProperty` {`description`:"Ein voller Name", `name_de`:"Voller Name", `scalartype`:"string", `shortname`:"name"})
create (_3:`SemRelation` {`description`:"A Label or Relation --SEMPROP-> Property", `shortname`:"SEMPROP"})
create (_4:`SemLabel` {`description`:"The meta label to label labels", `shortname`:"SemLabel"})
create (_5:`SemProperty` {`description`:"Der intern benutzte Bezeichner", `name_de`:"Kurzname", `scalartype`:"string", `shortname`:"shortname"})
create (_6:`SemProperty` {`description`:"Vorname einer Person", `name_de`:"Vorname", `scalartype`:"string", `shortname`:"firstname"})
create (_7:`SemProperty` {`description`:"Eine Beschreibung", `name_de`:"Beschreibung", `scalartype`:"string", `shortname`:"description"})
create (_8:`SemLabel` {`description`:"A description of  property of semantic meta object", `shortname`:"SemProperty"})
create (_9:`SemProperty` {`description`:"The last name of a person", `name_de`:"Nachname", `scalartype`:"string", `shortname`:"lastname"})
create (_11:`SemProperty` {`description`:"Der Klarname", `name_de`:"Bezeichnung", `scalartype`:"string", `shortname`:"name_de"})
create (_12:`SemProperty` {`description`:"Von welchem Typ ist der Wert", `name_de`:"Scalarer Typ", `scalartype`:"string", `shortname`:"scalartype"})
create (_13:`SemLabel` {`description`:"used to define a type of relation", `shortname`:"SemRelation"})
create (_14:`SemProperty` {`description`:"Wie oft darf es die Eigenschaft geben", `name_de`:"Anzahl", `scalartype`:"string", `shortname`:"arity"})
create (_21:`Person` {`name`:"Bob"})
create (_22:`SemRelation` {`description`:"xoxoxo", `shortname`:"MAG"})
create (_0)-[:`MAG`]->(_21)
create (_1)-[:`SEMPROP` {`arity`:"?"}]->(_9)
create (_1)-[:`SEMPROP` {`arity`:"?"}]->(_6)
create (_1)-[:`SEMPROP` {`arity`:"1"}]->(_2)
create (_3)-[:`SEMPROP` {`arity`:1}]->(_14)
create (_4)-[:`SEMPROP` {`arity`:"1"}]->(_7)
create (_4)-[:`SEMPROP` {`arity`:"1"}]->(_5)
create (_8)-[:`SEMPROP` {`arity`:1}]->(_12)
create (_8)-[:`SEMPROP` {`arity`:1}]->(_11)
create (_8)-[:`SEMPROP` {`arity`:1}]->(_7)
create (_8)-[:`SEMPROP` {`arity`:"1"}]->(_5)
create (_13)-[:`SEMPROP` {`arity`:"1"}]->(_5)
create (_13)-[:`SEMPROP` {`arity`:"1"}]->(_7)
create (_21)-[:`MAG`]->(_0)
;