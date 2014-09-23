Instance descriptors
====================

.. contents::

Abstract
--------

Instances generated from software release take parameters (typically to
customise instantiation and instance behaviour) and publish results
(typically allowing access to requester). This also applies not only to
the root software instance, but to any instance requested by another
instance.

The structure of these values is constrained by how the Software Release
was implemented, and must be documented so it can be used. Instance
descriptors are intended to provide such documentation in a form
allowing automated generation of a user interface to consult and provide
parameters, and to consult published results.

Specification
-------------

Instance parameters (=requests) and published results (=responses) are
specified using json schemas, as defined in the following resources:

- http://tools.ietf.org/html/draft-zyp-json-schema-03#section-5.20
- http://tools.ietf.org/html/draft-zyp-json-schema-04
- http://json-schema.org/

These schema MUST ignore any technical overhead, such as
serialisation-format-imposed layers (such as
``<?xml ...?><instance></instance>`` level in ``xml`` serialisation,
or the ``<prameter id="_">`` level in ``json-in-xml`` serialisation).

Rules to define access to request & response schemas for a given
software release and software type should be provided in a file whose
name is deduced from the software release URL by appending ".json" to
its path component. Components preceding path (scheme & netloc) MUST
be preserved, components succeeding path (query & fragment) SHOULD be
preserved. If a file actually resides at such URL, it MUST be valid
json syntax and satisfy the following json schema::

  {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "description": "Slapos Software Release instantiation descriptor",
    "additionalProperties": false,
    "properties": {
      "name": {
        "description": "A short human-friendly name for the sofware release",
        "type": "string"
      },
      "description": {
        "description": "A short description of the sofware release",
        "type": "string"
      },
      "serialisation": {
        "description": "How the parameters and results are serialised",
        "required": true,
        "enum": ["xml", "json-in-xml"],
        "type": "string"
      },
      "software-type": {
        "description": "Existing software types",
        "required": true,
        "patternProperties": {
          ".*": {
            "description": "Software type declaration",
            "additionalProperties": false,
            "properties": {
              "description": {
                "description": "A human-friendly description of the software type",
                "type": "string"
              },
              "serialisation": {
                "description": "How the parameters and results are serialised, if different from global setting",
                "enum": ["xml", "json-in-xml"],
                "type": "string"
              },
              "request": {
                "required": true,
                "description": "URL, relative to Software Release base path, of a json schema for values expected by instance of current software type",
                "type": "string"
              },
              "response": {
                "required": true,
                "description": "URL, relative to Software Release base path, of a json schema for values published by instance of current software type",
                "type": "string"
              },
              "index": {
                "description": "Value to use instead of software type id to sort them (in order to display most relevant software types earlier in a list, for example)",
                "type": "any"
              }
            },
            "type": "object"
          }
        },
        "type": "object"
      }
    },
    "type": "object"
  }

Error handling
--------------

If instantiation descriptor does not exist, is not valid json or does
not conform to this schema, it is ignored and a fall-back
representation is used. Likewise, if a software type of an existing
instance is not defined in software-type object or referenced schema
does not exist or is invalid, the same fall-back representation is used
for considered software type.

A fall-back representation must allow full control to the user, without
any guided editing: user is expected to serialise on his own and
provides & receives raw strings as request and responses, respectively.

Request schemas, when present and valid, MAY be used to validate user
input.

It SHOULD be made possible for user to violate the schema just as it is
possible for existing instances to already violate schemas. These
violation should be represented in a way which makes as much sense as
possible: displaying recursively all object properties and iteratively
all list items with as appropriate as possible fields, with a fall-back
on free text input. These extra fields generated from existing data or
created on-the-fly by the user MUST NOT prevent schema-conforming
fields from being displayed and functional.

