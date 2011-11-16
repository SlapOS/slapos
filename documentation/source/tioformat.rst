Tio Format
**********

What is TioFormat?
------------------

TIO is a data format used to provide informations about consumption, invoicing
and state history.

XSD
---

`TioFormat XSD`::

  <?xml version="1.0" encoding="utf-8"?>
  <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <!-- Define the XML Schema of a transaction -->
    <xs:element name="journal">
      <xs:complexType>
        <xs:sequence>
          <xs:element name="transaction" maxOccurs="unbounded">
            <xs:complexType>
              <xs:sequence>
                <xs:element name="title" type="xs:string" minOccurs="0"/>
                <xs:element name="start_date" type="xs:string"/>
                <xs:element name="stop_date" type="xs:string"/>
                <xs:element name="reference" type="xs:string"/>
                <xs:element name="currency" type="xs:string"/>
                <xs:element name="payment_mode" type="xs:string"/>
                <xs:element name="category" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
                <xs:element name="arrow" maxOccurs="unbounded">
                  <xs:complexType>
                    <xs:sequence>
                    <xs:element name="source" type="xs:string" minOccurs="0"/>
                    <xs:element name="destination" type="xs:string" minOccurs="0"/>
                    </xs:sequence>
                    <xs:attribute name="type" use="required"/>
                  </xs:complexType>
                </xs:element>
                <xs:element name="movement" maxOccurs="unbounded">
                  <xs:complexType>
                    <xs:sequence>
                    <xs:element name="resource" type="xs:string"/>
                    <xs:element name="title" type="xs:string" minOccurs="0"/>
                    <xs:element name="reference" type="xs:string" minOccurs="0"/>
                    <xs:element name="quantity" type="xs:float"/>
                    <xs:element name="price" type="xs:float"/>
                    <xs:element name="VAT" type="xs:string"/>
                    <xs:element name="category" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
                    </xs:sequence>
                  </xs:complexType>
                </xs:element>
              </xs:sequence>
              <xs:attribute name="type" use="required"/>
            </xs:complexType>
          </xs:element>
        </xs:sequence>
      </xs:complexType>
    </xs:element>
  </xs:schema>

Schema Components
-----------------

Element: ``journal``
++++++++++++++++++++

=============== =======
`Name`          journal
`Type`          journal
`Documentation` journal is the root element in the XML file
=============== =======

`Schema Component Representation`::

  <xs:element name="journal">

Complex Type: ``journal``
+++++++++++++++++++++++++

=============== =======
`Name`          journal
`Documentation` Tio document contains transactions
=============== =======

`Schema Component Representation`::

  <xs:complexType>
    <xs:sequence>
      <xs:element name="transaction" maxOccurs="unbounded">
      </xs:element>
    </xs:sequence>
  </xs:complexType>

Complex Type: ``transaction``
+++++++++++++++++++++++++++++

=============== =======
`Name`          transaction
`Documentation` transaction contains a title, a start_date, a stop_date, a reference, a currency, a payment mode, some categories, some arrows and a list of movement.
=============== =======

`Schema Component Representation`::

  <xs:complexType>
    <xs:sequence>
      <xs:element name="title" type="xs:string" minOccurs="0"/>
      <xs:element name="start_date" type="xs:string"/>
      <xs:element name="stop_date" type="xs:string"/>
      <xs:element name="reference" type="xs:string"/>
      <xs:element name="currency" type="xs:string"/>
      <xs:element name="payment_mode" type="xs:string"/>
      <xs:element name="category" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
      <xs:element name="arrow" maxOccurs="unbounded">
      </xs:element>
      <xs:element name="movement" maxOccurs="unbounded">
        </xs:complexType>
      </xs:element>
    </xs:sequence>
    <xs:attribute name="type" use="required"/>
  </xs:complexType>

Element: ``title``
++++++++++++++++++

=============== =======
`Name`          title
`Type`          string
`Documentation` title is the name of the transaction
=============== =======

`Schema Component Representation`::

  <xs:element name="title" type="xs:string" minOccurs="0"/>

Element: ``start_date``
+++++++++++++++++++++++

=============== =======
`Name`          start_date
`Type`          string
`Documentation` the date at which a service started
=============== =======

`Schema Component Representation`::

  <xs:element name="start_date" type="xs:string"/>

Element: ``stop_date``
++++++++++++++++++++++

=============== =======
`Name`          stop_date
`Type`          string
`Documentation` the date at which a service was completed
=============== =======

`Schema Component Representation`::

  <xs:element name="stop_date" type="xs:string"/>

Element: ``reference``
++++++++++++++++++++++

=============== =======
`Name`          reference
`Type`          string
`Documentation` absolute reference of the transaction
=============== =======

`Schema Component Representation`::

  <xs:element name="reference" type="xs:string"/>

Element: ``currency``
+++++++++++++++++++++

=============== =======
`Name`          currency
`Type`          string
`Documentation` currency used in the transaction
=============== =======

`Schema Component Representation`::

  <xs:element name="currency" type="xs:string"/>

Element: ``payment_mode``
+++++++++++++++++++++++++

=============== =======
`Name`          payment_mode
`Type`          string
`Documentation` payment mode of the transaction
=============== =======

`Schema Component Representation`::

  <xs:element name="payment_mode" type="xs:string"/>

Element: ``category``
+++++++++++++++++++++

=============== =======
`Name`          category
`Type`          string
`Documentation` To add your own category section in the transaction
=============== =======

`Schema Component Representation`::

  <xs:element name="category" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>

Element: ``arrow``
++++++++++++++++++

=============== =======
`Name`          arrow
`Type`          arrow
`Documentation` represents who provided a service to somebody else
=============== =======

`Schema Component Representation`::

  <xs:element name="arrow" maxOccurs="unbounded">

Complex Type: ``arrow``
+++++++++++++++++++++++

=============== =======
`Name`          arrow
`Documentation` contains a source and a destination.
=============== =======

`Schema Component Representation`::

  <xs:complexType>
    <xs:sequence>
    <xs:element name="source" type="xs:string" minOccurs="0"/>
    <xs:element name="destination" type="xs:string" minOccurs="0"/>
    </xs:sequence>
    <xs:attribute name="type" use="required"/>
  </xs:complexType>

Element: ``source``
+++++++++++++++++++

=============== =======
`Name`          source
`Type`          string
`Documentation` who provided the service
=============== =======

`Schema Component Representation`::

  <xs:element name="source" type="xs:string" minOccurs="0"/>

Element: ``destination``
++++++++++++++++++++++++

=============== =======
`Name`          destination
`Type`          string
`Documentation` who received the service
=============== =======

`Schema Component Representation`::

  <xs:element name="destination" type="xs:string" minOccurs="0"/>

Element: ``movement``
+++++++++++++++++++++

=============== =======
`Name`          movement
`Type`          movement
`Documentation` represents how much service exchanged in the transaction
=============== =======

`Schema Component Representation`::

  <xs:element name="movement" maxOccurs="unbounded">

Complex Type: ``movement``
++++++++++++++++++++++++++

=============== =======
`Name`          movement
`Documentation` contains a resource, a title, a reference, a quantity, a price, a VAT and some categories
=============== =======

`Schema Component Representation`::

  <xs:complexType>
    <xs:sequence>
    <xs:element name="resource" type="xs:string"/>
    <xs:element name="title" type="xs:string" minOccurs="0"/>
    <xs:element name="reference" type="xs:string" minOccurs="0"/>
    <xs:element name="quantity" type="xs:float"/>
    <xs:element name="price" type="xs:float"/>
    <xs:element name="VAT" type="xs:string"/>
    <xs:element name="category" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    </xs:sequence>
  </xs:complexType>

Element: ``resource``
+++++++++++++++++++++

=============== =======
`Name`          resource
`Type`          string
`Documentation` represents the kind of service provided
=============== =======

`Schema Component Representation`::

  <xs:element name="resource" type="xs:string"/>

Element: ``quantity``
+++++++++++++++++++++

=============== =======
`Name`          quantity
`Type`          float
`Documentation` represents the amount of service exchanged
=============== =======

`Schema Component Representation`::

  <xs:element name="quantity" type="xs:string"/>

Element: ``price``
++++++++++++++++++

=============== =======
`Name`          price
`Type`          float
`Documentation` represents the price of service exchanged
=============== =======

`Schema Component Representation`::

  <xs:element name="price" type="xs:string"/>

Element: ``VAT``
++++++++++++++++

=============== =======
`Name`          VAT
`Type`          string
`Documentation` represents the VAT of service exchanged
=============== =======

`Schema Component Representation`::

  <xs:element name="VAT" type="xs:string"/>

