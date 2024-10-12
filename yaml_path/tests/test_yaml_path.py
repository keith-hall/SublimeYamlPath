import unittest
from textwrap import dedent
from yaml_path.yaml_path import parse_yaml_docs, yaml_path_to
from ruamel.yaml import YAML


class TestJsonPath(unittest.TestCase):
    JSON_CONTENT = dedent("""\
        {
            "foo": "bar",
            "baz": "some escape chars C:\\Program Files",
            "bay": "some escape chars C:\\Program Files\\\\",
            "bax": "this is a \\"quote\\" test",
            "baw": "escaped slashes before quote \\\\",
            "quoted-key": 123,
            "quoted.key": [
                7,
                8,
                {
                    "nested": ["test"]
                },
                9, # supports trailing commas!
            ],
            "keywithslash\\"": null,
            // and kinda some JSONC comments
        }
    """)

    def setUp(self) -> None:
        self.doc = parse_yaml_docs(self.JSON_CONTENT)

    def test_json(self) -> None:
        result = yaml_path_to(self.doc, 1, 5)
        self.assertEqual(result, 'foo')

        result = yaml_path_to(self.doc, 3, 20)
        self.assertEqual(result, 'bay')

        result = yaml_path_to(self.doc, 6, 20)
        self.assertEqual(result, '["quoted-key"]')

        result = yaml_path_to(self.doc, 11, 14)
        self.assertEqual(result, '["quoted.key"][2].nested')

        # nested on same line not supported yet
        # result = yaml_path_to(self.doc, 11, 30)
        # self.assertEqual(result, '["quoted.key"][2].nested[0]')

        result = yaml_path_to(self.doc, 13, 13)
        self.assertEqual(result, '["quoted.key"][3]')

        result = yaml_path_to(self.doc, 15, 13)
        self.assertEqual(result, '["keywithslash\\""]')


class TestYamlPath(unittest.TestCase):
    YAML_CONTENT = dedent("""\
        services:
          traefik:
            image: traefik:v1.7.34-alpine
            container_name: traefik-dev-proxy
            restart: always
            ports:
              - "80:80"
              - "443:443"
              - "8686:8686"
            networks:
              some-network:
                aliases:
                  - some.domain
                  - sub.some.domain # some comment here
            volumes:
              - $PWD/traefik/traefik.toml:/etc/traefik/traefik.toml
              - $PWD/traefik/certs:/certs
              - /var/run/docker.sock:/var/run/docker.sock

    """)

    MULTI_DOC = YAML_CONTENT + "\n" + dedent("""\
        ---
        - test: a
        - match: 'foo'
          scope: bar
    """)

    def test_yaml(self) -> None:
        doc = parse_yaml_docs(self.YAML_CONTENT)

        result = yaml_path_to(doc, 0, 0)
        self.assertEqual(result, 'services')

        result = yaml_path_to(doc, 1, 5)
        self.assertEqual(result, 'services.traefik')

        # mapping key
        result = yaml_path_to(doc, 3, 10)
        self.assertEqual(result, 'services.traefik.container_name')

        # mapping value
        result = yaml_path_to(doc, 3, 30)
        self.assertEqual(result, 'services.traefik.container_name')

        # sequence element
        result = yaml_path_to(doc, 7, 20)
        self.assertEqual(result, 'services.traefik.ports[1]')

        # key which needs to be quoted in the path
        result = yaml_path_to(doc, 12, 30)
        self.assertEqual(result, 'services.traefik.networks["some-network"].aliases[0]')

        # after all the mappings in the document
        result = yaml_path_to(doc, 18, 1)
        self.assertEqual(result, '')

    def test_multidoc_yaml(self) -> None:
        docs = parse_yaml_docs(self.MULTI_DOC)
        print(docs)
        print(self.MULTI_DOC)

        # TODO: just call all the same tests as for single doc here?
        result = yaml_path_to(docs, 0, 0)
        self.assertEqual(result, 'services')

        # new doc line
        result = yaml_path_to(docs, 19, 1)
        self.assertEqual(result, '')

        result = yaml_path_to(docs, 21, 1)
        self.assertEqual(result, '[0]')

        result = yaml_path_to(docs, 23, 1)
        self.assertEqual(result, '[1].scope')


if __name__ == '__main__':
    unittest.main()


def run_tests():
    suite = unittest.makeSuite(TestYamlPath)
    runner = unittest.TextTestRunner()
    runner.run(suite)

# python3 -m yaml_path.test_yaml_path
