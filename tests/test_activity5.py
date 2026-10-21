import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from access_control import ROLE_PERMISSION_MATRIX, seed_access_control
from database.database import Base
from graphql_schema import schema
from models.models import CompanyUserRole, FinancialTransaction, Role, RolePermission


class RolesAndPermissionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        seed_access_control(self.db)
        self.context = {"db": self.db, "current_user": None, "auth_error": None}

    def tearDown(self):
        self.db.close()

    # ---------- helpers ----------
    def run_gql(self, document, variables=None):
        return schema.execute_sync(document, variable_values=variables, context_value=self.context)

    def ok(self, document, variables=None):
        result = self.run_gql(document, variables)
        self.assertIsNone(result.errors, result.errors)
        return result.data

    def role_id(self, code):
        return str(self.db.query(Role).filter(Role.code == code).one().id)

    def make_company(self, name="Empresa A", prefix="a"):
        company_id = self.ok(
            'mutation($n: String!) { createCompany(input: {name: $n}) { id } }', {"n": name}
        )["createCompany"]["id"]
        admin = self.ok(
            """mutation($i: CreateCompanyAdminInput!) { createCompanyAdmin(input: $i) { id } }""",
            {"i": {"companyId": company_id, "name": "Admin", "email": f"{prefix}-admin@example.com",
                   "password": "ClaveSegura123"}},
        )["createCompanyAdmin"]["id"]
        return company_id, admin

    def make_member(self, company_id, admin_id, role_code, email):
        member_id = self.ok(
            """mutation($i: CreateCompanyUserInput!, $a: ID!) {
              createCompanyUser(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"companyId": company_id, "name": email, "email": email, "password": "ClaveSegura123"},
             "a": admin_id},
        )["createCompanyUser"]["id"]
        self.ok(
            """mutation($i: AssignRoleInput!, $a: ID!) {
              assignRole(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"companyUserId": member_id, "roleId": self.role_id(role_code)}, "a": admin_id},
        )
        return member_id

    def create_account(self, company_id, actor, name="Caja"):
        return self.run_gql(
            """mutation($i: CreateAccountInput!, $a: ID!) {
              createAccount(input: $i, actorCompanyUserId: $a) { id name } }""",
            {"i": {"companyId": company_id, "accountType": "CASH", "name": name}, "a": actor},
        )

    # ---------- parte 1: catálogos ----------
    def test_catalogs_are_seeded_once(self):
        roles = self.ok("query { roles { code } }")["roles"]
        self.assertEqual(
            [r["code"] for r in roles], ["ADMINISTRADOR", "CONTADOR", "CAPTURISTA", "CONSULTA"]
        )
        self.assertEqual(len(self.ok("query { permissions { code } }")["permissions"]), 10)
        seed_access_control(self.db)  # "reinicio"
        self.assertEqual(self.db.query(Role).count(), 4)
        self.assertEqual(
            self.db.query(RolePermission).count(),
            sum(len(v) for v in ROLE_PERMISSION_MATRIX.values()),
        )

    def test_create_and_deactivate_role_and_unique_codes(self):
        data = self.ok('mutation { createRole(input: {code: "auditor", name: "Auditor"}) { id code isActive } }')
        self.assertEqual(data["createRole"]["code"], "AUDITOR")
        dup = self.run_gql('mutation { createRole(input: {code: "AUDITOR", name: "Otro"}) { id } }')
        self.assertIn("Ya existe un rol", str(dup.errors))
        role_id = data["createRole"]["id"]
        off = self.ok(f'mutation {{ deactivateRole(id: "{role_id}") {{ isActive }} }}')
        self.assertFalse(off["deactivateRole"]["isActive"])
        self.assertEqual(self.db.query(Role).filter(Role.code == "AUDITOR").count(), 1)  # no se borra
        self.ok('mutation { createPermission(input: {code: "reports.read", name: "Ver reportes"}) { id } }')
        dup = self.run_gql('mutation { createPermission(input: {code: "reports.read", name: "x"}) { id } }')
        self.assertIn("Ya existe un permiso", str(dup.errors))

    # ---------- parte 2: matriz ----------
    def test_role_permission_matrix(self):
        def codes(role_code):
            data = self.ok(
                f'query {{ rolePermissions(roleId: "{self.role_id(role_code)}") {{ permission {{ code }} }} }}'
            )
            return {row["permission"]["code"] for row in data["rolePermissions"]}

        for role_code, expected in ROLE_PERMISSION_MATRIX.items():
            self.assertEqual(codes(role_code), set(expected), role_code)
        self.assertIn("transactions.write", codes("CAPTURISTA"))
        self.assertNotIn("accounts.write", codes("CAPTURISTA"))
        self.assertFalse([c for c in codes("CONSULTA") if c.endswith(".write")])

    def test_assign_and_remove_permission_to_role(self):
        _, admin = self.make_company()
        perm_id = str(self.db.query(RolePermission).first().permission_id)
        # accounts.write al capturista (no lo tenía)
        from models.models import Permission
        accounts_write = str(self.db.query(Permission).filter(Permission.code == "accounts.write").one().id)
        mutation = """mutation($i: AssignPermissionToRoleInput!, $a: ID!) {
          assignPermissionToRole(input: $i, actorCompanyUserId: $a) { isActive } }"""
        variables = {"i": {"roleId": self.role_id("CAPTURISTA"), "permissionId": accounts_write}, "a": admin}
        self.ok(mutation, variables)
        self.assertIn("ya está asignado", str(self.run_gql(mutation, variables).errors))
        remove = """mutation($r: ID!, $p: ID!, $a: ID!) {
          removePermissionFromRole(roleId: $r, permissionId: $p, actorCompanyUserId: $a) }"""
        self.ok(remove, {"r": self.role_id("CAPTURISTA"), "p": accounts_write, "a": admin})
        row = self.db.query(RolePermission).filter(
            RolePermission.role_id == int(self.role_id("CAPTURISTA")),
            RolePermission.permission_id == int(accounts_write),
        ).one()
        self.assertFalse(row.is_active)  # desactivada, no borrada
        self.ok(mutation, variables)  # se puede volver a activar
        self.assertIsNotNone(perm_id)

    # ---------- parte 1/2: administrador principal ----------
    def test_admin_gets_role_and_second_admin_still_fails(self):
        company_id, admin = self.make_company()
        data = self.ok(f'query {{ companyUsers(companyId: "{company_id}", actorCompanyUserId: "{admin}") '
                       f'{{ isAdmin role {{ code }} }} }}')
        self.assertEqual(data["companyUsers"][0]["role"]["code"], "ADMINISTRADOR")
        self.assertTrue(data["companyUsers"][0]["isAdmin"])
        second = self.run_gql(
            """mutation($i: CreateCompanyAdminInput!) { createCompanyAdmin(input: $i) { id } }""",
            {"i": {"companyId": company_id, "name": "B", "email": "b@example.com", "password": "ClaveSegura123"}},
        )
        self.assertIn("ya tiene un administrador", str(second.errors))

    def test_assign_role_keeps_one_active_role_and_admin_rules(self):
        company_id, admin = self.make_company()
        member = self.make_member(company_id, admin, "CAPTURISTA", "ana@example.com")
        mutation = """mutation($i: AssignRoleInput!, $a: ID!) {
          assignRole(input: $i, actorCompanyUserId: $a) { isActive role { code } } }"""
        self.ok(mutation, {"i": {"companyUserId": member, "roleId": self.role_id("CONTADOR")}, "a": admin})
        active = self.db.query(CompanyUserRole).filter(
            CompanyUserRole.company_user_id == int(member), CompanyUserRole.is_active.is_(True)
        ).all()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].role.code, "CONTADOR")
        # volver a un rol anterior reactiva la fila, sigue habiendo uno solo
        self.ok(mutation, {"i": {"companyUserId": member, "roleId": self.role_id("CAPTURISTA")}, "a": admin})
        self.assertEqual(
            self.db.query(CompanyUserRole).filter(
                CompanyUserRole.company_user_id == int(member), CompanyUserRole.is_active.is_(True)
            ).count(), 1)
        # reglas del administrador principal
        bad = self.run_gql(mutation, {"i": {"companyUserId": member, "roleId": self.role_id("ADMINISTRADOR")}, "a": admin})
        self.assertIn("exclusivo del administrador principal", str(bad.errors))
        bad = self.run_gql(mutation, {"i": {"companyUserId": admin, "roleId": self.role_id("CONSULTA")}, "a": admin})
        self.assertIn("debe conservar el rol ADMINISTRADOR", str(bad.errors))

    # ---------- parte 3: operaciones protegidas ----------
    def test_transactions_capturista_ok_consulta_rejected(self):
        company_id, admin = self.make_company()
        capturista = self.make_member(company_id, admin, "CAPTURISTA", "cap@example.com")
        consulta = self.make_member(company_id, admin, "CONSULTA", "con@example.com")
        account_id = self.create_account(company_id, admin).data["createAccount"]["id"]
        concept_id = self.ok(
            """mutation($i: CreateConceptInput!, $a: ID!) {
              createConcept(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"companyId": company_id, "conceptType": "INCOME", "name": "Venta"}, "a": admin},
        )["createConcept"]["id"]
        self.ok(
            """mutation($i: AssignConceptToAccountInput!, $a: ID!) {
              assignConceptToAccount(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"accountId": account_id, "conceptId": concept_id}, "a": admin},
        )
        mutation = """mutation($i: CreateTransactionInput!, $a: ID!) {
          createTransaction(input: $i, actorCompanyUserId: $a) { id capturedBy } }"""
        variables = {"i": {"accountId": account_id, "conceptId": concept_id,
                           "transactionType": "INCOME", "amount": "100"}}
        accepted = self.ok(mutation, {**variables, "a": capturista})
        self.assertIsNotNone(accepted["createTransaction"]["id"])
        before = self.db.query(FinancialTransaction).count()
        rejected = self.run_gql(mutation, {**variables, "a": consulta})
        self.assertIn("transactions.write", str(rejected.errors))
        self.db.expire_all()
        self.assertEqual(self.db.query(FinancialTransaction).count(), before)  # no gana fila

    def test_create_account_by_role_and_role_change(self):
        company_id, admin = self.make_company()
        contador = self.make_member(company_id, admin, "CONTADOR", "con@example.com")
        capturista = self.make_member(company_id, admin, "CAPTURISTA", "cap@example.com")
        self.assertIsNone(self.create_account(company_id, contador, "Cuenta contador").errors)
        rejected = self.create_account(company_id, capturista, "Cuenta capturista")
        self.assertIn("accounts.write", str(rejected.errors))
        # assignRole: capturista -> contador, y ahora sí puede
        self.ok(
            """mutation($i: AssignRoleInput!, $a: ID!) {
              assignRole(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"companyUserId": capturista, "roleId": self.role_id("CONTADOR")}, "a": admin},
        )
        self.assertIsNone(self.create_account(company_id, capturista, "Cuenta capturista").errors)

    def test_reads_and_writes_need_permission(self):
        company_id, admin = self.make_company()
        capturista = self.make_member(company_id, admin, "CAPTURISTA", "cap@example.com")
        consulta = self.make_member(company_id, admin, "CONSULTA", "con@example.com")
        # capturista no tiene company.users.read ni roles.write
        denied = self.run_gql(
            f'query {{ companyUsers(companyId: "{company_id}", actorCompanyUserId: "{capturista}") {{ id }} }}')
        self.assertIn("company.users.read", str(denied.errors))
        denied = self.run_gql(
            """mutation($i: AssignRoleInput!, $a: ID!) {
              assignRole(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"companyUserId": capturista, "roleId": self.role_id("CONTADOR")}, "a": capturista})
        self.assertIn("roles.write", str(denied.errors))
        # consulta lee cuentas pero no crea conceptos ni usuarios
        self.ok(f'query {{ accounts(companyId: "{company_id}", actorCompanyUserId: "{consulta}") {{ id }} }}')
        denied = self.run_gql(
            """mutation($i: CreateConceptInput!, $a: ID!) {
              createConcept(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"companyId": company_id, "conceptType": "INCOME", "name": "X"}, "a": consulta})
        self.assertIn("concepts.write", str(denied.errors))
        denied = self.run_gql(
            """mutation($i: CreateCompanyUserInput!, $a: ID!) {
              createCompanyUser(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"companyId": company_id, "name": "N", "email": "n@example.com", "password": "ClaveSegura123"},
             "a": consulta})
        self.assertIn("company.users.write", str(denied.errors))

    def test_membership_without_role_or_inactive_is_rejected(self):
        company_id, admin = self.make_company()
        no_role = self.ok(
            """mutation($i: CreateCompanyUserInput!, $a: ID!) {
              createCompanyUser(input: $i, actorCompanyUserId: $a) { id } }""",
            {"i": {"companyId": company_id, "name": "S", "email": "s@example.com", "password": "ClaveSegura123"},
             "a": admin})["createCompanyUser"]["id"]
        self.assertIn("no tiene un rol activo", str(self.create_account(company_id, no_role).errors))

    def test_companies_do_not_mix(self):
        company_a, admin_a = self.make_company("Empresa A", "a")
        company_b, admin_b = self.make_company("Empresa B", "b")
        # el administrador de A no puede escribir ni leer en B
        denied = self.create_account(company_b, admin_a)
        self.assertIn("no pertenece a la empresa", str(denied.errors))
        denied = self.run_gql(
            f'query {{ accounts(companyId: "{company_b}", actorCompanyUserId: "{admin_a}") {{ id }} }}')
        self.assertIn("no pertenece a la empresa", str(denied.errors))
        # un movimiento de B no aparece en las consultas de A
        self.create_account(company_b, admin_b, "Caja B")
        data = self.ok(f'query {{ transactions(actorCompanyUserId: "{admin_a}") {{ id }} }}')
        self.assertEqual(data["transactions"], [])

    def test_bearer_token_must_match_actor(self):
        from models.models import User
        company_id, admin = self.make_company()
        other = self.make_member(company_id, admin, "CONTADOR", "otro@example.com")
        admin_user = self.db.query(User).filter(User.email == "a-admin@example.com").one()
        self.context["current_user"] = admin_user
        denied = self.create_account(company_id, other)
        self.assertIn("no corresponde al usuario autenticado", str(denied.errors))
        self.assertIsNone(self.create_account(company_id, admin).errors)


if __name__ == "__main__":
    unittest.main()
