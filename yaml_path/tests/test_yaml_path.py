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


class TestYamlPathMultilineString(unittest.TestCase):
    YAML_CONTENT = dedent("""\
        openapi: 3.0.3
        info:
          contact:
            email: noreply@example.com
            name: TestOpenAPISnippet
          description: Test OpenAPI snippet with
            multi-line strings so we can test the yaml path
          termsOfService: https://www.example.com/api-terms
          title: Example API
          version: 1.0
        servers:
          - url: /v1
        tags:
          - description: |-
              // Conditional snippet for beta or internal content
              include::../../maturity-admonition-banner.adoc[]

              Use the `/foo` endpoint to manage the example foos
            name: Some Tag
    """)

    def test_yaml(self) -> None:
        doc = parse_yaml_docs(self.YAML_CONTENT)

        result = yaml_path_to(doc, 0, 0)
        self.assertEqual(result, 'openapi')

        # info description line with key
        result = yaml_path_to(doc, 6, 20)
        self.assertEqual(result, 'info.description')

        # info description line after key
        result = yaml_path_to(doc, 7, 20)
        self.assertEqual(result, 'info.description')

        # tag description line with key
        result = yaml_path_to(doc, 15, 17)
        self.assertEqual(result, 'tags[0].description')

        # tag description 1 line below key
        result = yaml_path_to(doc, 16, 17)
        self.assertEqual(result, 'tags[0].description')

        # tag description 2 lines below key
        result = yaml_path_to(doc, 17, 17)
        self.assertEqual(result, 'tags[0].description')

        # after all the mappings in the document
        result = yaml_path_to(doc, 21, 1)
        self.assertEqual(result, '')


if __name__ == '__main__':
    unittest.main()


def run_tests():
    suite = unittest.makeSuite(TestYamlPath)
    runner = unittest.TextTestRunner()
    runner.run(suite)

