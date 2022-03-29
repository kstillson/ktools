
import context_kcore     # fix path to includes work as expected in tests

import kcore.common_base as C


def test_dict_to_list_of_pairs():
    assert C.dict_to_list_of_pairs({'b': 1, 'a': 2}) == [['a', 2], ['b', 1]]
    assert C.dict_to_list_of_pairs({}) == []

def test_list_to_csv():
    assert C.list_to_csv([[3, 2], [2, 1, 0]]) == '3, 2\n2, 1, 0\n'
    assert C.list_to_csv(C.dict_to_list_of_pairs({'b': 1, 'a': 2})) == 'a, 2\nb, 1\n'
    assert C.list_to_csv([]) == ''

def test_read_file():
    f = 'testdata/file1'
    assert C.read_file(f) == 'hello world \nline 2  \n   \n'
    assert C.read_file(f, strip=True) == 'hello world \nline 2'
    assert C.read_file(f, list_of_lines=True) == ['hello world ', 'line 2  ', '   ', '']
    assert C.read_file(f, list_of_lines=True, strip=True) == ['hello world', 'line 2', '']
    assert C.read_file('notfound') == None
    try:
        C.read_file('notfound', wrap_exceptions=False)
        assert '' == 'exception expected!'
    except IOError:  ## py2
        pass
    except FileNotFoundError:  ## py3
        pass

