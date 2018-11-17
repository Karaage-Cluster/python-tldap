import pytest

from tldap.dict import CaseInsensitiveDict, ImmutableDict


@pytest.fixture
def ci():
    """ Get group 1. """
    allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
    return CaseInsensitiveDict(allowed_values)


@pytest.fixture
def immutable():
    """ Get group 1. """
    allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
    return ImmutableDict(allowed_values)


class TestCaseInsensitive:
    def test_init_lowercase(self):
        allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
        ci = CaseInsensitiveDict(allowed_values, {'numberofpenguins': 10})
        assert ci.keys() == {'NumberOfPenguins'}

    def test_init_mixedcase(self, ci):
        allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
        ci = CaseInsensitiveDict(allowed_values, {'numberOFpenguins': 10})
        assert ci.keys() == {'NumberOfPenguins'}

    def test_init_uppercase(self, ci):
        allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
        ci = CaseInsensitiveDict(allowed_values, {'NUMBEROFPENGUINS': 10})
        assert ci.keys() == {'NumberOfPenguins'}

    def test_init_not_valid(self, ci):
        allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
        with pytest.raises(KeyError):
            CaseInsensitiveDict(allowed_values, {'numberOFfish': 10})

    def test_set_lowercase(self, ci):
        ci['numberofpenguins'] = 10
        assert ci.keys() == {'NumberOfPenguins'}

    def test_set_mixedcase(self, ci):
        ci['numberOFpenguins'] = 10
        assert ci.keys() == {'NumberOfPenguins'}

    def test_set_uppercase(self, ci):
        ci['NUMBEROFPENGUINS'] = 10
        assert ci.keys() == {'NumberOfPenguins'}

    def test_set_not_valid(self, ci):
        with pytest.raises(KeyError):
            ci['numberOFfish'] = 10

    def test_get(self, ci):
        ci['numberOFpenguins'] = 10
        assert ci['numberofpenguins'] == 10
        assert ci['NumberOfPenguins'] == 10
        assert ci['NUMBEROFPENGUINS'] == 10

    def test_get_not_set(self, ci):
        ci['numberOFpenguins'] = 10

        with pytest.raises(KeyError):
            assert ci['NumberOfSharks'] == 10

    def test_get_valid(self, ci):
        ci['numberOFpenguins'] = 10

        with pytest.raises(KeyError):
            assert ci['nUmberoFfIsh'] == 10


class TestImmutable:
    def test_init_lowercase(self):
        allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
        ci = ImmutableDict(allowed_values, {'numberofpenguins': 10})
        assert ci.keys() == {'NumberOfPenguins'}

    def test_init_mixedcase(self, ci):
        allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
        ci = ImmutableDict(allowed_values, {'numberOFpenguins': 10})
        assert ci.keys() == {'NumberOfPenguins'}

    def test_init_uppercase(self, ci):
        allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
        ci = ImmutableDict(allowed_values, {'NUMBEROFPENGUINS': 10})
        assert ci.keys() == {'NumberOfPenguins'}

    def test_init_not_valid(self, ci):
        allowed_values = {'NumberOfPenguins', 'NumberOfSharks'}
        with pytest.raises(KeyError):
            ImmutableDict(allowed_values, {'numberOFfish': 10})

    def test_set_fails(self, immutable):
        with pytest.raises(TypeError):
            immutable['numberofpenguins'] = 10
        with pytest.raises(TypeError):
            immutable['numberoffish'] = 10

    def test_set_lowercase(self, immutable):
        immutable = immutable.set('numberofpenguins', 10)
        assert immutable.keys() == {'NumberOfPenguins'}

    def test_set_mixedcase(self, immutable):
        immutable = immutable.set('numberOFpenguins', 10)
        assert immutable.keys() == {'NumberOfPenguins'}

    def test_set_uppercase(self, immutable):
        immutable = immutable.set('NUMBEROFPENGUINS', 10)
        assert immutable.keys() == {'NumberOfPenguins'}

    def test_set_not_valid(self, immutable):
        with pytest.raises(KeyError):
            immutable.set('numberOFfish', 10)

    def test_get(self, immutable):
        immutable = immutable.set('numberOFpenguins', 10)
        assert immutable['numberofpenguins'] == 10
        assert immutable['NumberOfPenguins'] == 10
        assert immutable['NUMBEROFPENGUINS'] == 10

    def test_get_not_set(self, immutable):
        immutable = immutable.set('numberOFpenguins', 10)

        with pytest.raises(KeyError):
            assert immutable['NumberOfSharks'] == 10

    def test_get_valid(self, immutable):
        immutable = immutable.set('numberOFpenguins', 10)

        with pytest.raises(KeyError):
            assert immutable['nUmberoFfIsh'] == 10

