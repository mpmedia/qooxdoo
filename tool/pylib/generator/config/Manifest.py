#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################################
#
#  qooxdoo - the new era of web development
#
#  http://qooxdoo.org
#
#  Copyright:
#    2006-2010 1&1 Internet AG, Germany, http://www.1und1.de
#
#  License:
#    LGPL: http://www.gnu.org/licenses/lgpl.html
#    EPL: http://www.eclipse.org/org/documents/epl-v10.php
#    See the LICENSE file in the project's top-level directory for details.
#
#  Authors:
#    * Thomas Herchenroeder (thron7)
#
################################################################################

##
# NAME
#  Manifest  -- class that represents a Manifest.json file, with operations
#
##

import os, sys, re, types, string, copy, codecs
from collections import defaultdict
from misc import json
from generator.config.ConfigurationError import ConfigurationError


class Manifest(object):
    def __init__(self, path):
        self.path = path
        try:
            mf = codecs.open(path, "r", "utf-8")
            manifest = json.loads(mf.read())
            mf.close()
        except Exception, e:
            msg = "Reading of manifest file failed: '%s'" % path + (
                "\n%s" % e.args[0] if e.args else "")
            e.args = (msg,) + e.args[1:]
            raise
        self._manifest = manifest
        self.libinfo     = self._manifest['info']
        self.libprovides = self._manifest['provides']

        self.namespace   = self.libprovides['namespace']
        self.encoding    = self.libprovides['encoding']
        # make the others optional
        self.classpath   = self.libprovides['class'] if 'class' in self.libprovides else None
        self.translation = self.libprovides['translation'] if 'translation' in self.libprovides else None
        self.resource    = self.libprovides['resource'] if 'resource' in self.libprovides else None
        self.type        = self.libprovides['type'] if 'type' in self.libprovides else None


    ##
    # Patches a "library" entry with the information from Manifest
    #
    def patchLibEntry(self, libentry):
        libinfo       = self._manifest['info']
        libprovides   = self._manifest['provides']
        #uriprefix = libentry['uri']
        uriprefix = ""
        libentry['class']         = os.path.join(uriprefix,libprovides['class'])
        libentry['resource']      = os.path.join(uriprefix,libprovides['resource'])
        libentry['translation']   = os.path.join(uriprefix,libprovides['translation'])
        if 'translation' in libprovides:
            libentry['translation']   = os.path.join(uriprefix,libprovides['translation'])
        libentry['encoding']    = libprovides['encoding']
        if 'namespace' in libentry:
            if libentry['namespace'] != libprovides['namespace']:
                raise ConfigurationError("Mismatch between Manifest namespace and directory namespaces")
        else:
            libentry['namespace']   = libprovides['namespace']
        libentry['type']        = libprovides['type']
        libentry['path']        = os.path.dirname(libentry['manifest']) or '.'

        # from the 'info' section
        if 'version' in libinfo:
            libentry['version'] = libinfo['version']
        if 'qooxdoo-versions' in libinfo:
            libentry['qooxdoo-versions'] = libinfo['qooxdoo-versions']
        if 'sourceViewUri' in libinfo:
            libentry['sourceViewUri'] = libinfo['sourceViewUri']

        return libentry


    ##
    # Catalog entry schema for catalog v1.0.
    #
    # The regexes strive to be lax (and understandable => part of err msg) but valuable
    # at the same time, cause we don't want to adapt them over and over again.
    #
    # Should be own file instead of dict, but then there would be no named regexes
    # and furthermore a regex DRY violation for multi-used regexes.
    #
    # Notes:
    #     * currently a query-string (?...) isn't allowed within an URL => change if needed
    #     * currently a fragment-identifier (#...) isn't allowed within an URL => change if needed
    #
    @classmethod
    def schema_v1_0(self):
        patterns = {
            "semver": r"^trunk$|master$|^\d+\.\d+(\.\d+)?(-[0-9]+-?)?([-a-zA-Z+][-a-zA-Z0-9.:-]*)?$",
            "url": r"^https?://([a-z0-9\.-]+)\.([a-z\.]{2,6})[/\w\.-]*\/?$",
            "url_and_placeholder": r"^https?://([a-z0-9\.-]+)\.([a-z\.]{2,6})[/\w.%{}-]*(#[/\w.%{}-]*)?\/?$",
            "url_archive": r"^(https?|ftp)://.*(tar(\.gz|\.bz2)?|tgz|zip)$",
            "name_and_github_uid": r"^.*\([\w.-]+\)$",
            "checksum": "^[a-f0-9]{40}$"  # has to be SHA-1
        }

        return {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "title": "Manifest.json",
            "type": "object",
            "required": ["info", "provides"],
            "properties": {
                "info": {
                    "type": "object",
                    "required": ["name", "description", "homepage", "license",
                                 "authors", "version", "qooxdoo-versions"],
                    "properties": {
                        "name": {
                            "type": "string",
                        },
                        "summary": {
                            "type": "string"
                        },
                        "description": {
                            "type": "string",
                        },
                        "category": {
                             "type": "array",
                             "items": { "enum": ["theme", "widget", "drawing",
                                                 "tool", "backend"] }
                        },
                        "keywords": {
                            "type": "array",
                            "uniqueItems": True,
                            "items": {
                                "type": "string"
                            },
                        },
                        "homepage": {
                            "type": "string",
                            "pattern": patterns["url"]
                        },
                        "license": {
                            "type": "string",
                        },
                        "authors": {
                            "type": "array",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {
                                "type": "object",
                                "required": ["name", "email"],
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "pattern": patterns["name_and_github_uid"]
                                    },
                                    "email": {
                                        "type": "string",
                                    }
                                }
                            }
                        },
                        "download": {
                            "type": "string",
                            "pattern": patterns["url_archive"]
                        },
                        "checksum": {
                            "type": "string",
                            "pattern": patterns["checksum"]
                        },
                        "version": {
                            "type": "string",
                            "pattern": patterns["semver"]
                        },
                        "qooxdoo-versions": {
                            "type": "array",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {
                                "type": "string",
                                "minItems": 1,
                                "pattern": patterns["semver"],
                            },
                        },
                        "sourceViewUri": {
                            "type": "string",
                            "pattern": patterns["url_and_placeholder"]
                        }
                    }
                },
                "provides": {
                    "type": "object",
                    "required": ["namespace", "encoding", "class", "resource",
                                 "translation", "type"],
                    "properties": {
                        "namespace": {
                            "type": "string",
                        },
                        "encoding": {
                            "type": "string",
                        },
                        "class": {
                            "type": "string",
                        },
                        "resource": {
                            "type": "string",
                        },
                        "translation": {
                            "type": "string",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["library", "application", "add-in"]
                        }
                    }
                }
            }
        }
