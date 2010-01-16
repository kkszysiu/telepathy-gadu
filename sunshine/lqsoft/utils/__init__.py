# -*- coding: utf-8

class Enum(object):
    def __init__(self, kwargs):
        self.__dict__['__dict'] = kwargs
        self.__dict__['__reverse_dict'] = {}
        for (k,v) in kwargs.iteritems():
            self.__dict__['__reverse_dict'][v] = k

    def key_for(self, name):
        return self.__reverse_dict[name]

    def __getattr__(self, name):
        try:
            return self.__dict__['__dict'][name]
        except KeyError:
            raise AttributeError('No attribute named ' + name)

    def __setattr__(self, name, value):
        raise AttributeError('This class in not mutable')


def reverse_dict(mapping):
    d = {}
    for (k,v) in mapping.iteritems():
        d[v] = k
    return mapping, d