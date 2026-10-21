import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from access_control import seed_access_control
from database.database import Base
import models.models  # noqa: F401
from models.models import User
from graphql_schema import schema


class GraphQLActivityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        seed_access_control(self.db)

    def tearDown(self):
        self.db.close()

    def execute(self, document, variables=None):
        return schema.execute_sync(document, variable_values=variables, context_value={"db": self.db})

    def test_complete_activity_flow_and_business_errors(self):
        company = self.execute(
            'mutation { createCompany(input: {name: "Empresa Uno", email: "info@example.com"}) { id name isActive } }'
        )
        self.assertIsNone(company.errors)
        company_id = company.data["createCompany"]["id"]

        companies = self.execute("query { companies(activeOnly: true) { id name } }")
        self.assertEqual(companies.data["companies"][0]["name"], "Empresa Uno")
        updated = self.execute(
            f'mutation {{ updateCompany(input: {{id: "{company_id}", phone: "9991234567"}}) {{ phone }} }}'
        )
        self.assertEqual(updated.data["updateCompany"]["phone"], "9991234567")

        admin_mutation = """mutation Admin($input: CreateCompanyAdminInput!) {
          createCompanyAdmin(input: $input) { id isAdmin role { code } user { email } }
        }"""
        admin = self.execute(admin_mutation, {"input": {
            "companyId": company_id, "name": "Admin", "email": "ADMIN@EXAMPLE.COM",
            "password": "ClaveSegura123",
        }})
        self.assertIsNone(admin.errors)
        self.assertTrue(admin.data["createCompanyAdmin"]["isAdmin"])
        self.assertEqual(admin.data["createCompanyAdmin"]["role"]["code"], "ADMINISTRADOR")
        admin_id = admin.data["createCompanyAdmin"]["id"]
        self.assertEqual(admin.data["createCompanyAdmin"]["user"]["email"], "admin@example.com")
        stored_user = self.db.query(User).filter(User.email == "admin@example.com").one()
        self.assertNotEqual(stored_user.password_hash, "ClaveSegura123")
        self.assertTrue(stored_user.password_hash.startswith("pbkdf2_sha256$"))

        second_admin = self.execute(admin_mutation, {"input": {
            "companyId": company_id, "name": "Admin 2", "email": "admin2@example.com",
            "password": "ClaveSegura123",
        }})
        self.assertIn("ya tiene un administrador", str(second_admin.errors))

        user_mutation = """mutation User($input: CreateCompanyUserInput!) {
          createCompanyUser(input: $input, actorCompanyUserId: "%s") { id isAdmin user { email } }
        }""" % admin_id
        variables = {"input": {"companyId": company_id, "name": "Usuario",
                                "email": "user@example.com", "password": "ClaveSegura456"}}
        self.assertIsNone(self.execute(user_mutation, variables).errors)
        self.assertIn("ya está registrado", str(self.execute(user_mutation, variables).errors))
        members = self.execute(
            f'query {{ companyUsers(companyId: "{company_id}", actorCompanyUserId: "{admin_id}") {{ id isAdmin user {{ email }} }} }}'
        )
        self.assertEqual(len(members.data["companyUsers"]), 2)

        missing = {"input": dict(variables["input"], companyId="999")}
        self.assertIn("no pertenece a la empresa", str(self.execute(user_mutation, missing).errors))

        login = self.execute(
            'mutation { login(input: {email: "admin@example.com", password: "ClaveSegura123"}) { token tokenType user { email } } }'
        )
        self.assertIsNone(login.errors)
        self.assertEqual(login.data["login"]["tokenType"], "Bearer")
        self.assertEqual(len(login.data["login"]["token"].split(".")), 3)

        bad_login = self.execute(
            'mutation { login(input: {email: "admin@example.com", password: "incorrecta"}) { token } }'
        )
        self.assertIn("incorrectos", str(bad_login.errors))


if __name__ == "__main__":
    unittest.main()
