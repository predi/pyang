"""sid plugin

Plugin used to generate or update .sid files.
Please refer to [I-D.ietf-core-sid], [I-D.ietf-core-comi], [I-D.ietf-core-yang-cbor]
and [I-D.ietf-core-yang-library] for more information.

"""

import optparse
import sys
import collections
import re
import os
import errno
import json
from json import JSONDecodeError
import copy

from pyang import plugin
from pyang import util
from pyang import error
from pyang import syntax

try:
    string_types = basestring  # Python 2
except NameError:
    string_types = str  # Python 3

def pyang_plugin_init():
    plugin.register_plugin(SidPlugin())

class SidPlugin(plugin.PyangPlugin):

    def add_opts(self, optparser):
        optlist = [
            optparse.make_option("--sid-help",
                                 dest="sid_help",
                                 action="store_true",
                                 help="Print help on automatic SID generation"),
            optparse.make_option("--sid-generate-file",
                                 action="store",
                                 type="string",
                                 dest="generate_sid_file",
                                 help="Generate a .sid file."),
            optparse.make_option("--sid-update-file",
                                 action="store",
                                 type="string",
                                 dest="update_sid_file",
                                 help="Generate a .sid file based on a previous .sid file."),
            optparse.make_option("--sid-check-file",
                                 action="store",
                                 type="string",
                                 dest="check_sid_file",
                                 help="Check the consistency between a .sid file "
                                 "and the .yang file(s)."),
            optparse.make_option("--sid-list",
                                 action="store_true",
                                 dest="list_sid",
                                 help="Print the list of SID."),
            optparse.make_option("--sid-registration-info",
                                 action="store_true",
                                 dest="sid_registration_info",
                                 help="Print the information required by the SID registry."),
            optparse.make_option("--sid-extra-range",
                                 action="store",
                                 type="string",
                                 dest="extra_sid_range",
                                 help="Add an extra SID range during a .sid file update."),
            optparse.make_option("--sid-check-file-valid",
                                 action="store",
                                 type="string",
                                 dest="check_sid_file_valid",
                                 help="Check whether an existing .sid file is valid and "
                                      "has been generated for .yang file(s)."),
            ]

        g = optparser.add_option_group("SID file specific options")
        g.add_options(optlist)

    def setup_ctx(self, ctx):
        if ctx.opts.sid_help:
            print_help()
            sys.exit(0)

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False

    def post_validate_ctx(self, ctx, modules):
        nbr_option_specified = 0
        if ctx.opts.generate_sid_file is not None:
            nbr_option_specified += 1
        if ctx.opts.update_sid_file is not None:
            nbr_option_specified += 1
        if ctx.opts.check_sid_file is not None:
            nbr_option_specified += 1
        if ctx.opts.check_sid_file_valid is not None:
            nbr_option_specified += 1
        if nbr_option_specified == 0:
            return
        if nbr_option_specified > 1:
            sys.stderr.write("Invalid option, only one process on .sid file can be requested.\n")
            return

        fatal_error = False
        for _, etag, _ in ctx.errors:
            if not error.is_warning(error.err_level(etag)):
                fatal_error = True

        if fatal_error or ctx.errors and ctx.opts.check_sid_file is not None:
            sys.stderr.write("Invalid YANG module\n")
            return

        sid_file = SidFile()

        if ctx.opts.sid_registration_info:
            sid_file.sid_registration_info = True

        if ctx.opts.generate_sid_file is not None:
            sid_file.range = ctx.opts.generate_sid_file
            sid_file.is_consistent = False
            sid_file.sid_file_created = True

        if ctx.opts.update_sid_file is not None:
            sid_file.input_file_name = ctx.opts.update_sid_file
            sid_file.update_file = True

        if ctx.opts.check_sid_file is not None:
            sid_file.input_file_name = ctx.opts.check_sid_file
            sid_file.check_consistency = True
            if not sid_file.sid_registration_info:
                print("Checking consistency of '%s'" % sid_file.input_file_name)

        if ctx.opts.extra_sid_range is not None:
            if ctx.opts.update_sid_file is not None:
                sid_file.extra_range = ctx.opts.extra_sid_range
            else:
                sys.stderr.write(
                    "An extra SID range can be specified only during a .sid file update.\n")
                return

        if ctx.opts.list_sid:
            sid_file.list_content = True

        if ctx.opts.check_sid_file_valid is not None:
            sid_file.input_file_name = ctx.opts.check_sid_file_valid
            sid_file.check_validity = True

        try:
            sid_file.process_sid_file(modules[0])

        except SidParsingError as e:
            sys.stderr.write("ERROR, %s\n" % e)
        except SidFileError as e:
            sys.stderr.write("ERROR in '%s', %s\n" % (sid_file.input_file_name, e))
        except EnvironmentError as e:
            if e.errno == errno.ENOENT:
                sys.stderr.write("ERROR, file '%s' not found\n" % e.filename)
            else:
                sys.stderr.write("ERROR, in file '%s' " % e.filename)
        except JSONDecodeError as e:
            sys.stderr.write("ERROR in '%s', %s\n" % (sid_file.input_file_name, e))
        except ValueError as e:
            sys.stderr.write("ERROR in '%s', invalid JSON content\n" % sid_file.input_file_name)
        else:
            sys.exit(0)
        sys.exit(1)

def print_help():
    print("""
YANG Schema Item iDentifiers (SID) are globally unique unsigned integers used
to identify YANG items. SIDs are used instead of names to save space in
constrained applications such as COREconf. This plugin is used to automatically
generate and updated .sid files used to persist and distribute SID assignments.


COMMANDS

pyang [--sid-list] --sid-generate-file {count | entry-point:size} yang-filename
pyang [--sid-list] --sid-update-file sid-filename yang-filename
      [--sid-extra-range {count | entry-point:size}]
pyang [--sid-list] --sid-check-file sid-filename yang-filename


OPTIONS

--sid-generate-file

  This option is used to generate a new .sid file from a YANG module.

  Two arguments are required to generate a .sid file; the SID range assigned to
  the YANG module and its definition file. The SID range specified is a
  sub-range within a range obtained from a registrar or a sub-range within the
  experimental range (i.e. 60000 to 99999). The SID range consists of the first
  SID of the range, followed by a colon, followed by the number of SID
  allocated to the YANG module. The filename consists of the module name,
  followed by an @ symbol, followed by the module revision, followed by the
  ".yang" extension.

  This example shows how to generate the file toaster@2009-11-20.sid.

  $ pyang --sid-generate-file 20000:100 toaster@2009-11-20.yang

--sid-update-file

  Each time new items are added to a YANG module by the introduction of a new
  revision of this module, its included sub-modules or imported modules, the
  associated .sid file need to be updated. This is done by using the
  --sid-update-file option.

  Two arguments are required to generate a .sid file for an updated YANG
  module; the previous .sid file generated for the YANG module and the
  definition file of the updated module. Both filenames follow the usual
  naming conversion consisting of the module name, followed by an @ symbol,
  followed by the module revision, followed by the extension.

  This example shows how to generate the file toaster@2009-12-28.sid based
  on the SIDs already present in toaster@2009-11-20.sid.

  $ pyang --sid-update-file toaster@2009-11-20.sid toaster@2009-12-28.yang

-- sid-check-file

  The --sid-check-file option can be used at any time to verify if a .sid file
  need to be updated.

  Two arguments are required to verify a .sid file; the filename of the .sid
  file to be checked and the corresponding definition file.

  For example:

  $ pyang --sid-check-file toaster@2009-12-28.sid toaster@2009-12-28.yang

--sid-list

  The --sid-list option can be used before any of the previous options to
  obtains the list of SIDs assigned or validated. For example:

  $ pyang --sid-list --sid-generate-file 20000:100 toaster@2009-11-20.yang

--sid-extra-range

  If needed, an extra SID range can be assigned to an existing YANG module
  during its update with the --sid-extra-range option.

  For example, this command generates the file toaster@2009-12-28.sid using
  the initial range(s) present in toaster@2009-11-20.sid and the extra range
  specified in the command line.

  $ pyang --sid-update-file toaster@2009-11-20.sid
          toaster@2009-12-28.yang --sid-extra-range 20100:100

--sid-extra-range-count
  The number of SID required when generating or updating a .sid file can be
  computed by specifying "count" as SID range.

  For example:

  $ pyang --sid-generate-file count toaster@2009-11-20.yang
  or:

  $ pyang --sid-update-file toaster@2009-11-20.sid
          toaster@2009-12-28.yang --sid-extra-range count

--sid-check-file-valid

  The --sid-check-file-valid option can be used at any time to validate a .sid
  file against a .yang file. Validates the structure of .sid file and ensures
  that values such as identifiers in items reference definitions in .yang.

  Two arguments are required to verify a .sid file; the filename of the .sid
  file to be checked and the corresponding definition file.

  For example:

  $ pyang --sid-check-file-valid toaster@2009-12-28.sid toaster@2009-12-28.yang
""")

############################################################
class SidFileError(Exception):
    pass

class SidParsingError(Exception):
    """raised by plugins to fail the emit() function"""

############################################################
class SidFile:
    def __init__(self):
        self.sid_file_created = False
        self.is_consistent = True
        self.check_consistency = False
        self.list_content = False
        self.sid_registration_info = False
        self.input_file_name = None
        self.range = None
        self.extra_range = None
        self.count = False
        self.node_highest = 0
        self.content = collections.OrderedDict()
        self.module_name = ''
        self.module_revision = ''
        self.output_file_name = ''
        self.check_validity = False
        self.update_file = False

    def process_sid_file(self, module):
        self.module_name = module.i_modulename
        self.module_revision = util.get_latest_revision(module)
        self.output_file_name = '%s@%s.sid' % (self.module_name, self.module_revision)

        if self.range is not None:
            if self.range == 'count':
                self.count = True
            else:
                self.set_sid_range(self.range)

        if self.input_file_name is not None:
            if not self.input_file_name.endswith(".sid"):
                raise SidParsingError("File '%s' is not a .sid file" % self.input_file_name)

            with open(self.input_file_name) as f:
                self.content = json.load(f, object_pairs_hook=collections.OrderedDict)
            # Upgrades can be removed after a reasonable transition period.
            self.upgrade_sid_file_format(module)
            self.strip_wrapper()
            self.validate_key_and_value()
            self.normalize_key_names(self.content)
            if self.check_validity:
                self.validate_against_module(module)
            self.validate_overlapping_ranges()
            self.validate_sid()

            if self.check_validity:
                return

        if self.extra_range is not None:
            if self.extra_range == 'count':
                self.count = True
            else:
                self.set_sid_range(self.extra_range)
                self.validate_overlapping_ranges()

        self.set_module_information()
        self.collect_dependency_revision(module)
        self.collect_module_items(module)

        if self.range == 'count':
            number_of_unassigned_yang_items = self.number_of_unassigned_yang_items()
            print("\nThis YANG module requires %d SIDs." % number_of_unassigned_yang_items)
            return

        if self.extra_range == 'count':
            number_of_sids_allocated = self.number_of_sids_allocated()
            number_of_sids_used = self.number_of_sids_used()
            number_of_sids_available = number_of_sids_allocated - number_of_sids_used
            number_of_unassigned_yang_items = self.number_of_unassigned_yang_items()

            print("\nNumber of SIDs allocated to this module: %d" % number_of_sids_allocated)
            print("Number of SIDs required by this version: %d"
                  % (number_of_sids_used + number_of_unassigned_yang_items))
            if number_of_unassigned_yang_items > number_of_sids_available:
                print("\nAn extra range of at least %d SIDs is required to perform this update."
                      % (number_of_unassigned_yang_items - number_of_sids_available))
            else:
                print("\nThe update of the .sid file can be performed using "
                      "the currently available SIDs.")
            return

        self.sort_items()
        self.assign_sid()

        if self.list_content:
            self.list_all_items()
        else:
            self.list_deleted_items()

        if self.update_file:
            version = self.content.get('sid-file-version')
            if version is None:
                version = 1
            else:
                version = version + 1
            self.content['sid-file-version'] = version

        if self.check_consistency:
            if self.is_consistent:
                if self.sid_registration_info:
                    self.print_registration_information(module)
                else:
                    print("\nCheck completed successfully")
            else:
                print("\nThe .sid file needs to be updated.")
        else:
            if self.is_consistent:
                print("No .sid file generated, the current .sid file is already up to date.")
            else:
                self.generate_file()
                if self.sid_file_created:
                    print("\nFile %s created" % self.output_file_name)
                else:
                    print("\nFile %s updated" % self.output_file_name)

                print("Number of SIDs available : %d" % self.number_of_sids_allocated())
                print("Number of SIDs used : %d" % self.number_of_sids_used())


    ########################################################
    def set_sid_range(self, srange):
        match = re.match(r'^(\d+):(\d+)$', srange)
        if not match:
            raise SidParsingError("invalid range in argument, must be '<entry-point>:<size>'.")
        components = match.groups()

        aranges = self.content.get('assignment-range')
        if aranges is None:
            self.content['assignment-range'] = aranges = []
        aranges.append(collections.OrderedDict(
            [('entry-point', int(components[0])), ('size', int(components[1]))]))

    ########################################################
    # Set the 'module-name' and/or 'module-revision' in the .sid file if they differ
    def set_module_information(self):
        if self.module_name != self.content.get('module-name'):
            self.content['module-name'] = self.module_name
            if self.check_consistency:
                print("ERROR, Mismatch between the module name defined "
                      "in the .sid file and the .yang file.")
                self.is_consistent = False

        if self.module_revision != self.content.get('module-revision'):
            self.content['module-revision'] = self.module_revision
            if self.check_consistency:
                print("ERROR, Mismatch between the module revision defined "
                      "in the .sid file and the .yang file.")
                self.is_consistent = False

    ########################################################
    # Verify that .sid file contains a single top-level JSON object, named "ietf-sid-file:sid-file".
    def strip_wrapper(self):
        sid_file_absent = True
        for key in self.content:
            if key == 'ietf-sid-file:sid-file':
                sid_file_absent = False
                if not isinstance(self.content[key], collections.OrderedDict):
                    raise SidFileError("key 'ietf-sid-file:sid-file', invalid value.")
                self.content = self.content[key]  # strip wrapper
                break

            else:
                raise SidFileError("invalid field '%s'." % key)

        if sid_file_absent:
            raise SidFileError("mandatory object 'ietf-sid-file:sid-file' not present")

    ########################################################
    # Verify the tag and data type of each .sid file JSON object
    status_ends = ('unpublished', 'published')

    def validate_key_and_value(self):
        assignment_ranges_absent = True
        module_name_absent = True
        module_revision_absent = True
        items_absent = True

        for key in self.content:
            if key == 'assignment-range' or key == 'ietf-sid-file:assignment-range':
                assignment_ranges_absent = False
                if not isinstance(self.content[key], list):
                    raise SidFileError("key 'assignment-range', invalid  value.")
                self.validate_ranges(self.content[key])

            elif key == 'module-name' or key == 'ietf-sid-file:module-name':
                module_name_absent = False

            elif key == 'module-revision' or key == 'ietf-sid-file:module-revision':
                module_revision_absent = False

            elif key == 'description' or key == 'ietf-sid-file:description':
                if not (isinstance(self.content[key], string_types)):
                    raise SidFileError("invalid 'description' value '%s'." % self.content[key])

            elif key == 'sid-file-version' or key == 'ietf-sid-file:sid-file-version':
                if not (isinstance(self.content[key], int)):
                    raise SidFileError("invalid 'sid-file-version' value '%s'." % self.content[key])

            elif key == 'sid-file-status' or key == 'ietf-sid-file:sid-file-status':
                if not (isinstance(self.content[key], string_types)
                        and self.content[key].endswith(self.status_ends)):
                    raise SidFileError("invalid 'description' value '%s'." % self.content[key])

            elif key == 'dependency-revision' or key == 'ietf-sid-file:dependency-revision':
                if not isinstance(self.content[key], list):
                    raise SidFileError("key 'dependency-revision', invalid  value.")
                self.validate_dependency_revisions(self.content[key])

            elif key == 'item' or key == 'ietf-sid-file:item':
                items_absent = False
                if not isinstance(self.content[key], list):
                    raise SidFileError("key 'item', invalid value.")
                self.validate_items(self.content[key])

            else:
                raise SidFileError("invalid field '%s'." % key)

        if module_name_absent:
            raise SidFileError("mandatory field 'module-name' not present")

        if module_revision_absent:
            raise SidFileError("mandatory field 'module-revision' not present")

        if assignment_ranges_absent:
            raise SidFileError("mandatory field 'assignment-range' not present")

        if items_absent:
            raise SidFileError("mandatory field 'item' not present")

    def normalize_key_names(self, mapping):
        # goes through entire content recursively and replaces qualified key names with short
        # versions, for example 'ietf-sid-file:module-name' --> 'module-name'
        for _ in range(len(mapping)):
            k, v = mapping.popitem(False)
            components = k.split(':')
            if len(components) == 2 and components[0] == 'ietf-sid-file':
                old = k
                new = components[1]
            else:
                old = k
                new = k

            mapping[new if old == k else k] = v
            if isinstance(v, list):  # we only have leaf and list entries in there
                for entry in v:
                    self.normalize_key_names(entry)

    @staticmethod
    def validate_ranges(ranges):
        entry_point_absent = True
        size_absent = True

        for arange in ranges:
            for key in arange:
                if key == 'entry-point' or key == 'ietf-sid-file:entry-point':
                    entry_point_absent = False
                    if not isinstance(arange[key], string_types):  # YANG uint64 value
                        raise SidFileError("invalid 'entry-point' value '%s'." % arange[key])
                    try:
                        arange[key] = int(arange[key])  # integers internally
                    except ValueError:
                        raise SidFileError("invalid 'entry-point' value '%s'." % arange[key])

                elif key == 'size' or key == 'ietf-sid-file:size':
                    size_absent = False
                    if not isinstance(arange[key], string_types):  # YANG uint64 value
                        raise SidFileError("invalid 'size' value '%s'." % arange[key])
                    try:
                        arange[key] = int(arange[key])  # integers internally
                    except ValueError:
                        raise SidFileError("invalid 'size' value '%s'." % arange[key])

                else:
                    raise SidFileError("invalid key '%s'." % key)

        if entry_point_absent:
            raise SidFileError("mandatory field 'entry-point' not present")

        if size_absent:
            raise SidFileError("mandatory field 'size' not present")

    namespace_ends = ('module', 'identity', 'feature', 'data')

    def validate_items(self, items):
        namespace_absent = True
        identifier_absent = True
        sid_absent = True
        for item in items:
            for key in item:
                if key == 'namespace' or key == 'ietf-sid-file:namespace':
                    namespace_absent = False
                    if not (isinstance(item[key], string_types)
                            and item[key].endswith(self.namespace_ends)):
                        raise SidFileError("invalid 'namespace' value '%s'." % item[key])

                elif key == 'identifier' or key == 'ietf-sid-file:identifier':
                    identifier_absent = False
                    if not isinstance(item[key], string_types):
                        raise SidFileError("invalid 'identifier' value '%s'." % item[key])

                elif key == 'sid' or key == 'ietf-sid-file:sid':
                    sid_absent = False
                    if not isinstance(item[key], string_types):  # YANG uint64 value
                        raise SidFileError("invalid 'sid' value '%s'." % item[key])
                    try:
                        item[key] = int(item[key])  # integers internally
                    except ValueError:
                        raise SidFileError("invalid 'sid' value '%s'." % item[key])

                else:
                    raise SidFileError("invalid key '%s'." % key)

        if namespace_absent:
            raise SidFileError("mandatory field 'namespace' not present")

        if identifier_absent:
            raise SidFileError("mandatory field 'identifier' not present")

        if sid_absent:
            raise SidFileError("mandatory field 'sid' not present")

    def validate_dependency_revisions(self, items):
        module_name_absent = True
        revision_absent = True
        for item in items:
            for key in item:
                if key == 'module-name' or key == 'ietf-sid-file:module-name':
                    module_name_absent = False
                    if not (isinstance(item[key], string_types)):
                        raise SidFileError("invalid 'module-name' value '%s'." % item[key])

                elif key == 'module-revision' or key == 'ietf-sid-file:module-revision':
                    revision_absent = False
                    if not isinstance(item[key], string_types):
                        raise SidFileError("invalid 'module-revision' value '%s'." % item[key])

                else:
                    raise SidFileError("invalid key '%s'." % key)

        if module_name_absent:
            raise SidFileError("mandatory field 'module-name' not present")

        if revision_absent:
            raise SidFileError("mandatory field 'module-revision' not present")

    ########################################################
    # Verify if each range defined in the .sid file is distinct
    def validate_overlapping_ranges(self):
        assignment_ranges = self.content.get('assignment-range')
        if not assignment_ranges:
            return
        used = []

        for arange in assignment_ranges:
            low = arange['entry-point']
            high = low + arange['size']

            for used_low, used_high in used:
                if used_low <= low < used_high or low <= used_low < high:
                    raise SidFileError("overlapping ranges are not allowed.")
            used.append((low, high))

    ########################################################
    # Verify if each SID listed in items is in range and is not duplicate.
    def validate_sid(self):
        self.content['item'].sort(key=lambda item: item['sid'])
        last_sid = -1
        for item in self.content['item']:
            sid = item['sid']
            if self.out_of_ranges(sid):
                raise SidFileError("'sid' %d not within 'assignment-range'" % sid)
            if sid == last_sid:
                raise SidFileError("duplicated 'sid' value %d " % sid)
            last_sid = sid

    def out_of_ranges(self, sid):
        for arange in self.content.get('assignment-range') or []:
            if arange['entry-point'] <= sid < arange['entry-point'] + arange['size']:
                return False
        return True

    ########################################################
    # Verify that all values that reference YANG definitions in the .sid file are valid.
    def validate_against_module(self, module):
        valid = True
        name = self.content.get('module-name')
        if name != module.arg:
            valid = False
            print("ERROR, Mismatch between the module name defined in the .sid file ('%s') and "
                  "the .yang file ('%s')." % (name, module.arg))
        revision = self.content.get('module-revision')
        their_revision = util.get_latest_revision(module)
        if revision != their_revision:
            valid = False
            print("ERROR, Mismatch between the module revision defined in the .sid file ('%s') and "
                  "the .yang file ('%s')." % (revision, their_revision))
        dependency_revision = self.content.get('dependency-revision')
        if dependency_revision is not None:
            for dep in dependency_revision:
                name = dep.get('module-name')
                revision = dep.get('module-revision')
                key = (name, revision)
                if key not in module.i_ctx.modules:
                    print("WARNING, Dependency revision '%s%s' not found."
                          % (name, ("@" + revision) if key is not None else ""))
        elif module.search_one('import') is not None:
            print("WARNING, Found at least one import statement in .yang file but no dependency"
                  " revisions exist in .sid file")

        module_or_submodule = []
        for key in module.i_ctx.modules:
            entry = module.i_ctx.modules[key]
            if entry.keyword == 'submodule' or entry == module:
                module_or_submodule.append(entry.arg)
        for item in self.content['item']:
            namespace = item.get('namespace')
            identifier = item.get('identifier')
            if 'module' == namespace:
                if identifier not in module_or_submodule:
                    valid = False
                    print("ERROR, Item '%s' (%s) does not match any module or submodule." %
                          (identifier, namespace))
            elif 'feature' == namespace:
                if identifier not in module.i_features:
                    valid = False
                    print("ERROR, Item '%s' (%s) does not match any feature." %
                          (identifier, namespace))
            elif 'identity' == namespace:
                if identifier not in module.i_identities:
                    valid = False
                    print("ERROR, Item '%s' (%s) does not match any feature." %
                          (identifier, namespace))
            elif 'data' == namespace:
                if not self.check_data_identifier(identifier, module):
                    valid = False

        if not valid:
            raise SidFileError(".sid file does not match .yang file.")
        else:
            print("Check complete: .sid file matches .yang file.")

    def check_data_identifier(self, identifier, module):
        # this is a variant of statements.find_target_node(...)
        valid = True
        # parse the path into a list of two-tuples of (prefix,identifier)
        path = [(m[1], m[2]) for m in syntax.re_schema_node_id_part.findall(identifier)]
        if len(path) == 0:
            valid = False
            print("ERROR, Item '%s' (%s) not a valid schema node identifier."
                  % (identifier, 'data'))
        schema_node_module = None
        schema_node = None
        for module_name, name in path:
            if schema_node_module is None and module_name == '':
                valid = False
                print("ERROR, Item '%s' (%s) does not match an existing schema node - missing "
                      "module prefix in '%s'." % (identifier, 'data', "/" + name))
                break
            if module_name != '' and (
                    schema_node_module is None or schema_node_module.arg != module_name):
                schema_node_module = self.get_module_by_name(module_name, module)
                if schema_node_module is None:
                    valid = False
                    print("ERROR, Item '%s' (%s) does not match an existing schema node - "
                          "module '%s' in  '%s' not found."
                          % (identifier, 'data', module_name, "/" + module_name + ":" + name))
                    break
                if schema_node is None:
                    schema_node = schema_node_module
            schema_node = self.find_schema_node_child(name, schema_node, schema_node_module)
            if schema_node is None:
                valid = False
                print(
                    "ERROR, Item '%s' (%s) does not match an existing schema node - name '%s' not "
                    "found." % (identifier, 'data', name))
                break

        if valid and not self.is_from_same_namespace(schema_node, module):
            valid = False
            print("ERROR, Item '%s' (%s) does not identify a schema node from .yang file."
                  % (identifier, 'data'))

        return valid

    def find_schema_node_child(self, name, parent, module):
        child = None
        if hasattr(parent, 'i_children'):
            for candidate in parent.i_children:
                if name == candidate.arg and \
                        self.is_from_same_namespace(candidate, module):
                    child = candidate
                    break
        return child

    @staticmethod
    def get_module_by_name(module_name, module):
        revisions = []
        for (name, revision) in module.i_ctx.modules:
            if name == module_name:
                revisions.append(revision)

        if len(revisions) == 1:
            key = (module_name, revisions[0])
        else:
            revision = max(revisions)
            key = (module_name, revision)

        return module.i_ctx.modules[key]

    # Keywords that represent schema node items
    schema_node_keywords = ('action', 'container', 'leaf', 'leaf-list', 'list', 'choice', 'case',
                            'rpc', 'input', 'output',  'notification', 'anydata', 'anyxml',
                            ('ietf-restconf', 'yang-data'),
                            ('ietf-yang-structure-ext', 'structure'))

    @staticmethod
    def is_augment_structure_extension(statement):
        try:
            return statement.keyword == ('ietf-yang-structure-ext', 'augment-structure')
        except AttributeError:
            return False

    ########################################################
    # Collection of imports defined in .yang file(s)
    def collect_dependency_revision(self, module):
        self.content.pop('dependency-revision', None)  # reset
        for entry in module.i_ctx.modules:
            dependency = module.i_ctx.modules[entry]
            if dependency != module and dependency.keyword != 'submodule':
                (name, revision) = entry
                if 'dependency-revision' not in self.content:
                    self.content['dependency-revision'] = []
                dependency_revision = [('module-name', name)]
                if revision is not None:
                    dependency_revision.append(('module-revision', revision))
                self.content['dependency-revision'].append(
                    collections.OrderedDict(dependency_revision))

    ########################################################
    # Collection of items defined in .yang file(s)
    def collect_module_items(self, module):
        if 'item' not in self.content:
            self.content['item'] = []

        for item in self.content['item']:
            item['status'] = 'd' # Set to 'd' deleted, updated to 'o' if present in .yang file

        self.merge_item('module', self.module_name)

        for name in module.i_ctx.modules:
            if module.i_ctx.modules[name].keyword == 'submodule':
                self.merge_item('module', module.i_ctx.modules[name].arg)

        for feature in module.i_features:
            self.merge_item('feature', feature)

        self.iterate_schema_nodes(module, module, '')

        for identity in module.i_identities:
            self.merge_item('identity', identity)

        for substmt in module.substmts:
            if (substmt.keyword == 'augment' or self.is_augment_structure_extension(substmt))\
                    and hasattr(substmt, 'i_target_node'):
                self.iterate_schema_nodes(
                    substmt.i_target_node, module, self.get_path_to_root(substmt.i_target_node, module))

    def iterate_schema_nodes(self, parent, module, path):
        if not hasattr(parent, 'i_children'):
            return
        schema_nodes = parent.i_children
        if schema_nodes is None:
            return
        for schema_node in schema_nodes:
            if schema_node.i_module is not None \
                    and self.is_from_same_namespace(schema_node, module) \
                    and schema_node.keyword in self.schema_node_keywords:
                new_path = self.add_to_path(schema_node, parent, module, path)
                self.merge_item('data', new_path)
                self.iterate_schema_nodes(schema_node, module, new_path)

    def is_from_same_namespace(self, schema_node, module):
        if schema_node.i_module.keyword == 'submodule':
            return schema_node.i_module.i_ctx.get_module(
                schema_node.i_module.i_including_modulename) == module
        return schema_node.i_module == module

    def add_to_path(self, schema_node, parent, module, prefix=""):
        main_module = self.get_main_module(schema_node, module)
        if prefix == "" or main_module != self.get_main_module(parent, module):
            path = "/" + main_module.arg + ":" + schema_node.arg
        else:
            path = "/" + schema_node.arg

        return prefix + path

    def get_main_module(self, schema_node, module):
        if schema_node.i_module.keyword == 'submodule':
            main_module = self.get_module_by_name(schema_node.i_module.i_including_modulename, module)
        else:
            main_module = schema_node.i_module

        return main_module

    def get_path_to_root(self, schema_node, module):
        path_components = []

        while schema_node is not None:
            path_components.append(schema_node)
            schema_node = schema_node.parent

        path = ''
        size = len(path_components)
        for i in reversed(range(size)):
            node = path_components[i]
            if i == size - 1:
                pass  # module/submodule
            else:
                parent = path_components[i + 1]
                path = self.add_to_path(node, parent, module, path)

        return path

    def merge_item(self, namespace, identifier):
        for item in self.content['item']:
            if (namespace == item['namespace'] and identifier == item['identifier']):
                item['status'] = 'o' # Item already assigned
                return
        self.content['item'].append(collections.OrderedDict(
            [('namespace', namespace), ('identifier', identifier), ('sid', -1), ('status', 'n')]))
        self.is_consistent = False

    ########################################################
    # Sort the items list by 'namespace' and 'identifier'
    def sort_items(self):
        self.content['item'].sort(key=lambda item: item['identifier'])
        self.content['item'].sort(key=lambda item: item['namespace'], reverse=True)

    ########################################################
    # Identifier assignment
    def assign_sid(self):
        items = self.content['item']
        unassigned = [item for item in items if item['sid'] == -1]
        if not unassigned:
            return
        used = sorted(item['sid'] for item in items if item['sid'] != -1)
        needed = len(unassigned)
        source = self.gen_sids(used)

        for item in unassigned:
            try:
                item['sid'] = next(source)
            except StopIteration:
                raise SidParsingError(
                    "The current SID range(s) are exhausted, %d extra SID(s) "
                    "are required, use the --sid-extra-range option to add "
                    "a SID range to this YANG module." % needed)
            needed -= 1

    def sid_used(self, sid):
        for item in self.content['item']:
            if item['sid'] == sid:
                return True
        return False

    def gen_sids(self, used):
        ranges = sorted((arange['entry-point'], arange['size'])
                        for arange in self.content.get('assignment-range') or [])
        used_idx = 0
        used_len = len(used)
        for sid, size in ranges:
            high = sid + size
            while sid < high:
                # find next upper bound of unused sids above sid
                while used_idx < used_len:
                    stop = used[used_idx]
                    if stop < sid:
                        used_idx += 1
                    else:
                        if stop == sid:
                            # go past the used sid, recheck sid < high
                            sid += 1
                        elif stop > high:
                            # next used is above current range
                            stop = high
                        break
                else:
                    # no more used sids
                    stop = high

                while sid < stop:
                    yield sid
                    sid += 1

    ########################################################
    def list_all_items(self):
        definition_removed = False

        print("\nSID        Assigned to")
        print("---------  --------------------------------------------------")
        for item in self.content['item']:
            status = ""
            if item['status'] == 'n' and not self.sid_file_created:
                status = " (New)"
            if item['status'] == 'd' and item['namespace'] != 'module':
                status = " (Remove)"
                definition_removed = True

            print("%-9s  %s %s%s" % (item['sid'], item['namespace'], item['identifier'], status))

        if definition_removed:
            print(
                "\nWARNING, obsolete definitions should be defined as 'deprecated' or 'obsolete'.")

    ########################################################
    def list_deleted_items(self):
        definition_removed = False
        for item in self.content['item']:
            if item['status'] == 'd':
                print("WARNING, item '%s' was deleted form the .yang files." % item['identifier'])
                definition_removed = True

        if definition_removed:
            print("Obsolete definitions MUST NOT be removed "
                  "from YANG modules, see RFC 6020 section 10.\n"
                  "These definition(s) should be reintroduced "
                  "with a 'deprecated' or 'obsolete' status.")

    ########################################################
    def generate_file(self):
        for item in self.content['item']:
            del item['status']

        if os.path.exists(self.output_file_name):
            os.remove(self.output_file_name)

        with open(self.output_file_name, 'w') as outfile:
            json.dump(self.preprocess_content(), outfile, indent=2)

    ########################################################
    def preprocess_content(self):
        # leaves self.content intact, since it is needed later
        preprocessed = copy.deepcopy(self.content)
        # convert internal values to proper ones
        preprocessed = self.convert_yang_uin64_values(preprocessed)
        # reorder
        preprocessed = self.reorder_per_yang_model(preprocessed)
        # add wrapper
        preprocessed = collections.OrderedDict([('ietf-sid-file:sid-file', preprocessed)])
        return preprocessed

    ########################################################
    @staticmethod
    def reorder_per_yang_model(mapping):
        reordered = []

        def move(name):
            entry = mapping.pop(name, None)
            if entry is not None:
                reordered.append((name, entry))

        move('module-name')
        move('module-revision')
        move('sid-file-version')
        move('sid-file-status')
        move('description')
        move('dependency-revision')
        move('assignment-range')
        move('item')
        return collections.OrderedDict(reordered)

    ########################################################
    @staticmethod
    def convert_yang_uin64_values(mapping):
        if isinstance(mapping['assignment-range'], list):
            for assignment_range in mapping['assignment-range']:
                entry_point = assignment_range['entry-point']
                if isinstance(entry_point, util.int_types):
                    assignment_range['entry-point'] = str(entry_point)
                size = assignment_range['size']
                if isinstance(size, util.int_types):
                    assignment_range['size'] = str(size)
        if isinstance(mapping['assignment-range'], list):
            for item in mapping['item']:
                sid = item['sid']
                if isinstance(sid, util.int_types):
                    item['sid'] = str(sid)

        return mapping

    ########################################################
    def number_of_sids_allocated(self):
        size = 0
        for arange in self.content.get('assignment-range') or []:
            size += arange['size']
        return size

    def number_of_unassigned_yang_items(self):
        return len([0 for item in self.content['item'] if item['sid'] == -1])

    def number_of_sids_used(self):
        return len([0 for item in self.content['item'] if item['sid'] != -1])

    def number_of_sids_used_in_range(self, entry_point, size):
        low = entry_point
        high = low + size
        return len([0 for item in self.content['item'] if low <= item['sid'] < high])

    ########################################################
    def print_registration_information(self, module):
        ranges = []
        submodules = []
        info = {
            'module_name' : self.module_name,
            'module_revision' : self.module_revision,
            'yang_file' : '%s@%s.yang' % (self.module_name, self.module_revision),
            'ranges' : ranges,
            'submodules' : submodules,
        }

        for arange in self.content('assignment-range') or []:
            ranges.append({
                'entry_point' : arange['entry-point'],
                'size' : arange['size'],
                'used' : self.number_of_sids_used_in_range(arange['entry-point'], arange['size'])
            })

        for name in module.i_ctx.modules:
            submodule = module.i_ctx.modules[name]
            if submodule.keyword == 'submodule':
                submodules.append('%s@%s.yang' % (submodule.arg, submodule.i_latest_revision))

        print(json.dumps(info, indent=2))

    ########################################################
    # Perform the conversion to the .sid file format introduced by [I-D.ietf-core-sid] version 3.
    # This method can be removed after the proper transition period.

    node_keywords = ('node', 'notification', 'rpc', 'action')

    def upgrade_sid_file_format(self, module):
        if self.check_validity:
            return  # no fixes when checking whether .sid file valid

        items = self.content.get('items')
        if not items:
            return

        for item in items:
            type_ = item.pop('type', None)
            label = item.pop('label', None)
            if not type_:
                pass
            elif type_ in ('Module', 'Submodule'):
                item['namespace'] = 'module'
                item['identifier'] = label

            elif type_ == 'feature':
                item['namespace'] = type_
                item['identifier'] = label

            elif type_ == 'identity':
                item['namespace'] = type_
                item['identifier'] = label.rsplit('/', 1)[-1]

            elif type_ in self.node_keywords:
                item['namespace'] = 'data'
                item['identifier'] = '/' + self.module_name + ':' + label[1:]

        # legacy files generated wrong names; there is no 's' suffix for lists below
        items = self.content.pop('items', None)
        if items is not None:
            self.content['item'] = items
        assignment_ranges = self.content.pop('assignment-ranges', None)
        if assignment_ranges is not None:
            self.content['assignment-range'] = assignment_ranges

        # This plug-in used to generate JSON files that did not comply with RFC 7951, Section 6.1,
        # p2. The following method call tolerates such legacy files by converting all invalid values
        # into expected ones.
        self.convert_yang_uin64_values(self.content)

        # legacy .sid files did not contain the 'ietf-sid-file:sid-file' wrapper, this adds one
        if self.content.get('module-name') is not None:
            self.convert_legacy_paths_to_schema_node_paths(module)
            self.content = collections.OrderedDict([('ietf-sid-file:sid-file', self.content)])

    def convert_legacy_paths_to_schema_node_paths(self, module):
        # remove this method when upgrade_sid_file_format() is removed

        # legacy files did not emit choice and case nodes, rc:yang-data, etc. (except input/output)
        # this attempts to convert those paths into schema node identifiers
        items = self.content.get('item')
        if isinstance(items, list):
            for item in items:
                if isinstance(item, collections.OrderedDict) and item.get('namespace') == 'data':
                    path = item.get('identifier')
                    if path is not None and isinstance(path, string_types):
                        node = self.find_node_for_legacy_path(path, module)
                        if node is not None:
                            converted_path = self.get_path_to_root(node, module)
                            if converted_path != path:
                                item['identifier'] = converted_path

    def find_node_for_legacy_path(self, identifier, module):
        # remove this method when upgrade_sid_file_format() is removed
        valid = True
        path = [(m[1], m[2]) for m in syntax.re_schema_node_id_part.findall(identifier)]
        schema_node_module = None
        schema_node = None
        for module_name, name in path:
            if schema_node_module is None and module_name == '':
                valid = False
                break
            if module_name != '' and (
                    schema_node_module is None or schema_node_module.arg != module_name):
                schema_node_module = self.get_module_by_name(module_name, module)
                if schema_node_module is None:
                    valid = False
                    break
                if schema_node is None:
                    schema_node = schema_node_module
            schema_node = self.find_data_node_child(name, schema_node, schema_node_module)
            if schema_node is None:
                valid = False
                break

        return schema_node if valid else None

    ignorable_legacy_keywords = ('case', 'choice', ('ietf-restconf', 'yang-data'))

    def find_data_node_child(self, name, parent, module):
        # remove this method when upgrade_sid_file_format() is removed
        child = None
        if hasattr(parent, 'i_children'):
            for candidate in parent.i_children:
                if candidate.keyword in self.ignorable_legacy_keywords:
                    child = self.find_data_node_child(name, candidate, module)
                    if child is not None:
                        break
                elif name == candidate.arg and \
                        self.is_from_same_namespace(candidate, module):
                    child = candidate
                    break
        return child
