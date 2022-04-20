
import context_kcore     # fix path
import kcore.neo as N


def test_basics():
    p = N.Neo(n=8, simulation=True)

    p.fill(N.RED)
    assert p.get(5) == (255, 0, 0)

    p[2:3] = N.GREEN
    assert p.get(1) == (255, 0, 0)
    assert p.get(2) == (0, 255, 0)
    assert p.get(3) == (0, 255, 0)
    assert p.get(4) == (255, 0, 0)

    p[2:3] = [N.BLACK, N.BLUE]
    assert p.get(1) == (255, 0, 0)
    assert p.get(2) == (0, 0, 0)
    assert p.get(3) == (0, 0, 255)
    assert p.get(4) == (255, 0, 0)
    


def test_color_mappers():
    c = N.rgb_to_color(N.RED)
    assert c == 0xff0000

    assert N.color_to_rgb(c) == N.RED
