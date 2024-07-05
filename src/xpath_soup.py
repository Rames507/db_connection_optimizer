#!/usr/bin/python
# -*- coding: utf-8 -*-

# source: https://gist.github.com/ergoithz/6cf043e3fdedd1b94fcf#file-xpath_soup-py
# & https://stackoverflow.com/a/48376038


import typing

import bs4


def xpath_soup(element):
    # type: (typing.Union[bs4.element.Tag, bs4.element.NavigableString]) -> str
    """
    Generate xpath from BeautifulSoup4 element.

    :param element: BeautifulSoup4 element.
    :type element: bs4.element.Tag or bs4.element.NavigableString
    :return: xpath as string
    :rtype: str

    Usage
    -----
    >>> import bs4
    >>> html = (
    ...     '<html><head><title>title</title></head>'
    ...     '<body><p>p <i>1</i></p><p>p <i>2</i></p></body></html>'
    ...     )
    >>> soup = bs4.BeautifulSoup(html, 'html.parser')
    >>> xpath_soup(soup.html.body.p.i)
    '/html/body/p[1]/i'

    >>> import bs4
    >>> xml = (
    ...     '<?xml version="1.0" encoding="UTF-8"?>'
    ...     '<doc xmlns:ns1="http://localhost/ns1"'
    ...     '     xmlns:ns2="http://localhost/ns2">'
    ...     '<ns1:elm/><ns2:elm/><ns2:elm/></doc>'
    ...     )
    >>> soup = bs4.BeautifulSoup(xml, 'lxml-xml')
    >>> xpath_soup(soup.doc.find('ns2:elm').next_sibling)
    '/doc/ns2:elm[2]'

    """
    components = []
    target = element if element.name else element.parent
    for node in (target, *target.parents)[-2::-1]:  # type: bs4.element.Tag
        tag = "%s:%s" % (node.prefix, node.name) if node.prefix else node.name
        siblings = node.parent.find_all(tag, recursive=False)
        components.append(
            tag
            if len(siblings) == 1
            else "%s[%d]"
            % (
                tag,
                next(
                    index
                    for index, sibling in enumerate(siblings, 1)
                    if sibling is node
                ),
            )
        )
    return "/%s" % "/".join(components)


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True, raise_on_error=True)
