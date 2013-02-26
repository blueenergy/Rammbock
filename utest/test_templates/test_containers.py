from unittest import TestCase, main
from Rammbock.templates.containers import Protocol, MessageTemplate, StructTemplate, ListTemplate, UnionTemplate, BinaryContainerTemplate, TBCDContainerTemplate, ConditionalTemplate
from Rammbock.templates.primitives import UInt, PDU, Char
from Rammbock.binary_tools import to_bin_of_length, to_bin
from tools import *


class TestProtocol(TestCase):

    def setUp(self):
        self._protocol = Protocol('Test')

    def test_header_length(self):
        self._protocol.add(UInt(1, 'name1', None))
        self.assertEquals(self._protocol.header_length(), 1)

    def test_header_length_with_pdu(self):
        self._protocol.add(UInt(1, 'name1', None))
        self._protocol.add(UInt(2, 'name2', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length'))
        self.assertEquals(self._protocol.header_length(), 5)

    def test_verify_undefined_length(self):
        self._protocol.add(UInt(1, 'name1', None))
        self._protocol.add(UInt(2, 'name2', 5))
        self.assertRaises(Exception, self._protocol.add, PDU('length'))

    def test_verify_calculated_length(self):
        self._protocol.add(UInt(1, 'name1', 1))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-8'))
        self.assertEquals(self._protocol.header_length(), 3)


class TestMessageTemplate(TestCase):

    def setUp(self):
        self._protocol = Protocol('TestProtocol')
        self._protocol.add(UInt(2, 'msgId', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-4'))
        self.tmp = MessageTemplate('FooRequest', self._protocol, {})
        self.tmp.add(UInt(2, 'field_1', 1))
        self.tmp.add(UInt(2, 'field_2', 2))

    def test_create_template(self):
        self.assertEquals(len(self.tmp._fields), 2)

    def test_encode_template(self):
        msg = self.tmp.encode({}, {})
        self.assertEquals(msg.field_1.int, 1)
        self.assertEquals(msg.field_2.int, 2)

    def test_message_field_type_conversions(self):
        msg = self.tmp.encode({'field_1': 1024}, {})
        self.assertEquals(msg.field_1.int, 1024)
        self.assertEquals(msg.field_1.hex, '0x0400')
        self.assertEquals(msg.field_1.bytes, '\x04\x00')

    def test_encode_template_with_params(self):
        msg = self.tmp.encode({'field_1': 111, 'field_2': 222}, {})
        self.assertEquals(msg.field_1.int, 111)
        self.assertEquals(msg.field_2.int, 222)

    def test_encode_template_header(self):
        msg = self.tmp.encode({}, {})
        self.assertEquals(msg._header.msgId.int, 5)
        self.assertEquals(msg._header.length.int, 8)

    def test_encode_to_bytes(self):
        msg = self.tmp.encode({}, {})
        self.assertEquals(msg._header.msgId.int, 5)
        self.assertEquals(msg._raw, to_bin_of_length(8, '0x0005 0008 0001 0002'))

    # TODO: make the fields aware of their type?
    # so that uint fields are pretty printed to uints
    # bytes fields to hex bytes
    # and character fields to characters..
    def test_pretty_print(self):
        msg = self.tmp.encode({}, {})
        self.assertEquals(msg._header.msgId.int, 5)
        self.assertEquals(str(msg), 'Message FooRequest')
        self.assertEquals(repr(msg),
                          """Message FooRequest
  Header TestProtocol
    msgId = 5 (0x0005)
    length = 8 (0x0008)
  field_1 = 1 (0x0001)
  field_2 = 2 (0x0002)
""")

    def test_unknown_params_cause_exception(self):
        self.assertRaises(AssertionError, self.tmp.encode, {'unknown': 111}, {})

    def test_decode_message(self):
        msg = self.tmp.decode(to_bin('0xcafebabe'))
        self.assertEquals(msg.field_1.hex, '0xcafe')


class TestStructuredTemplate(TestCase):

    def test_access_struct(self):
        self._protocol = Protocol('TestProtocol')
        self._protocol.add(UInt(2, 'msgId', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-4'))
        self.tmp = MessageTemplate('StructuredRequest', self._protocol, {})
        struct = get_pair()
        self.tmp.add(struct)
        msg = self.tmp.encode({}, {})
        self.assertEquals(msg.pair.first.int, 1)

    def test_create_struct(self):
        struct = get_pair()
        self.assertEquals(struct.name, 'pair')

    def test_add_fields_to_struct(self):
        struct = get_pair()
        encoded = struct.encode({}, {})
        self.assertEquals(encoded.first.int, 1)

    def test_add_fields_to_struct_and_override_values(self):
        struct = get_pair()
        encoded = struct.encode({'pair.first': 42}, {})
        self.assertEquals(encoded.first.int, 42)

    def test_yo_dawg_i_heard(self):
        str_str = get_recursive_struct()
        encoded = str_str.encode({}, {})
        self.assertEquals(encoded.pair.first.int, 1)

    def test_get_recursive_names(self):
        pair = get_pair()
        names = pair._get_params_sub_tree({'pair.foo': 0, 'pairnotyourname.ploo': 2, 'pair.goo.doo': 3})
        self.assertEquals(len(names), 2)
        self.assertEquals(names['foo'], 0)
        self.assertEquals(names['goo.doo'], 3)

    def test_set_recursive(self):
        str_str = get_recursive_struct()
        encoded = str_str.encode({'str_str.pair.first': 42}, {})
        self.assertEquals(encoded.pair.first.int, 42)

    def test_decode_several_structs(self):
        str_list = get_struct_list()
        decoded = str_list.decode(to_bin('0xcafebabe d00df00d'), {})
        self.assertEquals(decoded[0].first.hex, '0xcafe')
        self.assertEquals(decoded[1].second.hex, '0xf00d')

    def test_length_of_struct(self):
        pair = get_pair()
        encoded = pair.encode({}, {})
        self.assertEquals(len(encoded), 4)

    def test_decode_struct(self):
        pair = get_pair()
        decoded = pair.decode(to_bin('0xcafebabe'), {})
        self.assertEquals(decoded.first.hex, '0xcafe')
        self.assertEquals(decoded.second.hex, '0xbabe')


class TestDefaultValues(TestCase):

    def test_default_values(self):
        pair = get_empty_pair()
        encoded = pair.encode({'pair.*': '5'})
        self.assertEquals(encoded.first.int, 5)

    def test_sub_default_values(self):
        pairs = get_empty_recursive_struct()
        encoded = pairs.encode({'*': '1', '3pairs.pair2.*': '2', '3pairs.pair3.*': '3'})
        self.assertEquals(encoded.pair1.first.int, 1)
        self.assertEquals(encoded.pair2.first.int, 2)
        self.assertEquals(encoded.pair3.first.int, 3)


class TestDynamicMessageTemplate(TestCase):

    def setUp(self):
        self._protocol = Protocol('TestProtocol')
        self._protocol.add(UInt(2, 'msgId', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-4'))

    def test_non_existing_dynamic_variable(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        self.assertRaises(Exception, tmp.add, Char('not_existing', 'foo', None))

    def test_non_existing_dynamic_list_variable(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        lst = ListTemplate('not_existing', 'foo', parent=None)
        lst.add(UInt(1, 'bar', None))
        self.assertRaises(Exception, tmp.add, lst)

    def test_decode_dynamic_primitive(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        tmp.add(UInt(1, 'len', None))
        tmp.add(Char('len', 'chars', None))
        tmp.add(UInt(1, 'len2', None))
        tmp.add(Char('len2', 'chars2', None))
        decoded = tmp.decode(to_bin('0x 04 6162 6364 02 6566'))
        self.assertEquals(decoded.len.int, 4)
        self.assertEquals(decoded.chars.ascii, 'abcd')
        self.assertEquals(decoded.chars2.ascii, 'ef')

    def test_encode_dynamic_primitive_with_defined_value(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        tmp.add(UInt(4, 'len', '4'))
        tmp.add(Char('len', 'chars', 'abcd'))
        tmp.add(UInt(4, 'len2', None))
        tmp.add(Char('len2', 'chars2', 'ef'))
        encoded = tmp.encode({'len2': '6'}, {})
        self.assertEquals(encoded.chars.ascii, 'abcd')
        self.assertEquals(len(encoded.chars), 4)
        self.assertEquals(encoded.chars2.ascii, 'ef')
        self.assertEquals(len(encoded.chars2), 6)

    def test_encode_dynamic_primitive_automatically(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        tmp.add(UInt(4, 'len', None))
        tmp.add(Char('len', 'chars', 'abcd'))
        encoded = tmp.encode({}, {})
        self.assertEquals(encoded.chars.ascii, 'abcd')
        self.assertEquals(encoded.len.int, 4)

    def test_decode_dynamic_list(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        tmp.add(UInt(2, 'len', None))
        lst = ListTemplate('len', 'foo', parent=None)
        lst.add(UInt(1, 'bar', None))
        tmp.add(lst)
        decoded = tmp.decode(to_bin('0x 00 04 6162 6364'))
        self.assertEquals(decoded.len.int, 4)
        self.assertEquals(decoded.foo[0].hex, '0x61')

    def test_encode_dynamic_list(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        tmp.add(UInt(2, 'len', None))
        lst = ListTemplate('len', 'foo', parent=None)
        lst.add(UInt(1, 'bar', 1))
        tmp.add(lst)
        encoded = tmp.encode({'len': 6}, {})
        self.assertEquals(len(encoded.foo), 6)

    def test_add_field_with_length_reference_to_parent(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        tmp.add(UInt(2, 'len', None))
        str = StructTemplate('FooType', 'foo', tmp)
        str.add(Char('len', "bar"))

    def test_add_field_with_length_reference_missing(self):
        tmp = MessageTemplate('Dymagic', self._protocol, {})
        tmp.add(UInt(2, 'len', None))
        str = StructTemplate('FooType', 'foo', tmp)
        self.assertRaises(AssertionError, str.add, Char('notfound', "bar"))


class TestMessageTemplateValidation(TestCase):

    def setUp(self):
        self._protocol = Protocol('TestProtocol')
        self._protocol.add(UInt(2, 'msgId', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-4'))
        self.tmp = MessageTemplate('FooRequest', self._protocol, {})
        self.tmp.add(UInt(2, 'field_1', '0xcafe'))
        self.tmp.add(UInt(2, 'field_2', '0xbabe'))

    def test_validate_passing_hex(self):
        msg = self.tmp.decode(to_bin('0xcafebabe'))
        errors = self.tmp.validate(msg, {})
        self.assertEquals(errors, [])

    def test_validate_error_default_value(self):
        msg = self.tmp.decode(to_bin('0xcafedead'))
        errors = self.tmp.validate(msg, {})
        self.assertEquals(errors, ['Value of field field_2 does not match 0xdead!=0xbabe'])

    def test_validate_error_override(self):
        msg = self.tmp.decode(to_bin('0xcafebabe'))
        errors = self.tmp.validate(msg, {'field_2': '0xdead'})
        self.assertEquals(errors, ['Value of field field_2 does not match 0xbabe!=0xdead'])

    def test_validate_two_errors(self):
        msg = self.tmp.decode(to_bin('0xbeefbabe'))
        errors = self.tmp.validate(msg, {'field_2': '0xdead'})
        self.assertEquals(len(errors), 2)

    def test_validate_pattern_pass(self):
        msg = self.tmp.decode(to_bin('0xcafe0002'))
        errors = self.tmp.validate(msg, {'field_2': '(0|2)'})
        self.assertEquals(len(errors), 0)

    def test_validate_pattern_failure(self):
        msg = self.tmp.decode(to_bin('0xcafe0002'))
        errors = self.tmp.validate(msg, {'field_2': '(0|3)'})
        self.assertEquals(len(errors), 1)

    def test_validate_passing_int(self):
        msg = self.tmp.decode(to_bin('0xcafe0200'))
        errors = self.tmp.validate(msg, {'field_2': '512'})
        self.assertEquals(errors, [])

    def test_failing_passing_int(self):
        msg = self.tmp.decode(to_bin('0xcafe0200'))
        errors = self.tmp.validate(msg, {'field_2': '513'})
        self.assertEquals(len(errors), 1)


class TestTemplateFieldValidation(TestCase, WithValidation):

    def test_validate_struct_passes(self):
        template = get_pair()
        field = template.encode({})
        self._should_pass(template.validate({'pair': field}, {'pair.first': '1'}))

    def test_validate_struct_fails(self):
        template = get_pair()
        field = template.encode({})
        self._should_fail(template.validate({'pair': field}, {'pair.first': '42'}), 1)

    def test_validate_list_succeeds(self):
        template = get_list_of_three()
        encoded = template.encode({}, None)
        self._should_pass(template.validate({'topthree': encoded}, {'topthree[1]': '1'}))

    def test_validate_list_fails(self):
        template = get_list_of_three()
        encoded = template.encode({}, None)
        self._should_fail(template.validate({'topthree': encoded}, {'topthree[1]': '42'}), 1)

    def test_validate_list_list(self):
        template = get_list_list()
        encoded = template.encode({}, None)
        self._should_pass(template.validate({'listlist': encoded}, {'listlist[1][1]': '7'}))
        self._should_fail(template.validate({'listlist': encoded}, {'listlist[1][1]': '42'}), 1)

    def test_validate_struct_list(self):
        template = get_struct_list()
        encoded = template.encode({}, None)
        self._should_pass(template.validate({'liststruct': encoded}, {'liststruct[1].first': '1'}))
        self._should_fail(template.validate({'liststruct': encoded}, {'liststruct[1].first': '42'}), 1)

    def test_dynamic_field_validation(self):
        struct = StructTemplate('Foo', 'foo', parent=None)
        struct.add(UInt(2, 'len', None))
        struct.add(Char('len', 'text', None))
        encoded = struct.encode({'foo.len': 6, 'foo.text': 'fobba'})
        self._should_pass(struct.validate({'foo': encoded}, {'foo.text': 'fobba'}))
        self._should_fail(struct.validate({'foo': encoded}, {'foo.text': 'fob'}), 1)


if __name__ == '__main__':
    main()
