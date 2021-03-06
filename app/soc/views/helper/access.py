#!/usr/bin/python2.5
#
# Copyright 2008 the Melange authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Access control helper.

The functions in this module can be used to check access control
related requirements. When the specified required conditions are not
met, an exception is raised. This exception contains a views that
either prompts for authentication, or informs the user that they
do not meet the required criteria.
"""

__authors__ = [
  '"Todd Larsen" <tlarsen@google.com>',
  '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  '"Lennard de Rijk" <ljvderijk@gmail.com>',
  '"Pawel Solyga" <pawel.solyga@gmail.com>',
  ]


from google.appengine.api import memcache

from django.utils.translation import ugettext

from soc.logic import dicts
from soc.logic import rights as rights_logic
from soc.logic.helper import timeline as timeline_helper
from soc.logic.models.club_admin import logic as club_admin_logic
from soc.logic.models.club_member import logic as club_member_logic
from soc.logic.models.document import logic as document_logic
from soc.logic.models.host import logic as host_logic
from soc.logic.models.mentor import logic as mentor_logic
from soc.logic.models.org_admin import logic as org_admin_logic
from soc.logic.models.organization import logic as org_logic
from soc.logic.models.program import logic as program_logic
from soc.logic.models.request import logic as request_logic
from soc.logic.models.role import logic as role_logic
from soc.logic.models.site import logic as site_logic
from soc.logic.models.sponsor import logic as sponsor_logic
from soc.logic.models.student import logic as student_logic
from soc.logic.models.student_project import logic as student_project_logic
from soc.logic.models.student_proposal import logic as student_proposal_logic
from soc.logic.models.timeline import logic as timeline_logic
from soc.logic.models.user import logic as user_logic
from soc.views.helper import redirects
from soc.views import out_of_band


DEF_NO_USER_LOGIN_MSG = ugettext(
    'Please create <a href="/user/create_profile">User Profile</a>'
    ' in order to view this page.')

DEF_AGREE_TO_TOS_MSG_FMT = ugettext(
    'You must agree to the <a href="%(tos_link)s">site-wide Terms of'
    ' Service</a> in your <a href="/user/edit_profile">User Profile</a>'
    ' in order to view this page.')

DEF_DEV_LOGOUT_LOGIN_MSG_FMT = ugettext(
    'Please <a href="%%(sign_out)s">sign out</a>'
    ' and <a href="%%(sign_in)s">sign in</a>'
    ' again as %(role)s to view this page.')

DEF_NEED_MEMBERSHIP_MSG_FMT = ugettext(
    'You need to be in the %(status)s group to %(action)s'
    ' documents in the %(prefix)s prefix.')

DEF_NEED_ROLE_MSG = ugettext(
    'You do not have the required role.')

DEF_NOT_YOUR_ENTITY_MSG = ugettext(
    'This entity does not belong to you.')

DEF_NO_ACTIVE_ENTITY_MSG = ugettext(
    'There is no such active entity.')

DEF_NO_ACTIVE_GROUP_MSG = ugettext(
    'There is no such active group.')

DEF_NO_ACTIVE_ROLE_MSG = ugettext(
    'There is no such active role.')

DEF_ALREADY_PARTICIPATING_MSG = ugettext(
    'You cannot become a Student because you are already participating '
    'in this program.')

DEF_ALREADY_STUDENT_ROLE_MSG = ugettext(
    'You cannot become a Mentor or Organization Admin because you already are '
    'a Student in this program.')

DEF_NO_ACTIVE_PROGRAM_MSG = ugettext(
    'There is no such active program.')

DEF_NO_REQUEST_MSG = ugettext(
    'There is no accepted request that would allow you to visit this page. '
    'Perhaps you already accepted this request?')

DEF_NO_APPLICATION_MSG = ugettext(
    'There is no application that would allow you to visit this page.')

DEF_NEED_PICK_ARGS_MSG = ugettext(
    'The "continue" and "field" args are not both present.')

DEF_REVIEW_COMPLETED_MSG = ugettext('This Application can not be reviewed '
    'anymore (it has been completed or rejected).')

DEF_REQUEST_COMPLETED_MSG = ugettext(
    'This request cannot be accepted (it is either completed or denied).')

DEF_SCOPE_INACTIVE_MSG = ugettext(
    'The scope for this request is not active.')

DEF_SIGN_UP_AS_STUDENT_MSG = ugettext(
    'You need to sign up as a Student first.')

DEF_MAX_PROPOSALS_REACHED = ugettext(
    'You have reached the maximum number of Proposals allowed '
    'for this program.')

DEF_NO_LIST_ACCESS_MSG = ugettext('You do not have the required rights to '
    'list documents for this scope and prefix.')

DEF_PAGE_DENIED_MSG = ugettext(
    'Access to this page has been restricted.')

DEF_PREFIX_NOT_IN_ARGS_MSG = ugettext(
    'A required GET url argument ("prefix") was not specified.')

DEF_PAGE_INACTIVE_MSG = ugettext(
    'This page is inactive at this time.')

DEF_LOGOUT_MSG_FMT = ugettext(
    'Please <a href="%(sign_out)s">sign out</a> in order to view this page.')

DEF_GROUP_NOT_FOUND_MSG = ugettext(
    'The requested Group can not be found.')

DEF_NOT_ALLOWED_PROJECT_FOR_SURVEY_MSG = ugettext(
    'You are not allowed to take this Survey for the specified Student'
    ' Project.')

DEF_NO_VALID_RECORD_ID = ugettext('No valid numeric record ID given.')

DEF_NOT_YOUR_RECORD = ugettext(
    'This is not your Survey Record. If you feel you should have access to '
    'this page please notify the administrators.')

DEF_USER_ACCOUNT_INVALID_MSG_FMT = ugettext(
    'The <b><i>%(email)s</i></b> account cannot be used with this site, for'
    ' one or more of the following reasons:'
    '<ul>'
    ' <li>the account is invalid</li>'
    ' <li>the account is already attached to a User profile and cannot be'
    ' used to create another one</li>'
    ' <li>the account is a former account that cannot be used again</li>'
    '</ul>')


class Error(Exception):
  """Base class for all exceptions raised by this module.
  """

  pass


class InvalidArgumentError(Error):
  """Raised when an invalid argument is passed to a method.

  For example, if an argument is None, but must always be non-False.
  """

  pass


def allowSidebar(fun):
  """Decorator that allows access if the sidebar is calling.
  """

  from functools import wraps

  @wraps(fun)
  def wrapper(self, django_args, *args, **kwargs):
    """Decorator wrapper method.
    """
    if django_args.get('SIDEBAR_CALLING'):
      return
    return fun(self, django_args, *args, **kwargs)
  return wrapper


def denySidebar(fun):
  """Decorator that denies access if the sidebar is calling.
  """

  from functools import wraps

  @wraps(fun)
  def wrapper(self, django_args, *args, **kwargs):
    """Decorator wrapper method.
    """
    if django_args.get('SIDEBAR_CALLING'):
      raise out_of_band.Error("Sidebar Calling")
    return fun(self, django_args, *args, **kwargs)
  return wrapper


def allowIfCheckPasses(checker_name):
  """Returns a decorator that allows access if the specified checker passes.
  """

  from functools import wraps

  def decorator(fun):
    """Decorator that allows access if the current user is a Developer.
    """

    @wraps(fun)
    def wrapper(self, django_args=None, *args, **kwargs):
      """Decorator wrapper method.
      """
      try:
        # if the check passes we allow access regardless
        return self.doCheck(checker_name, django_args, [])
      except out_of_band.Error:
        # otherwise we run the original check
        return fun(self, django_args, *args, **kwargs)
    return wrapper

  return decorator

# pylint: disable-msg=C0103
allowDeveloper = allowIfCheckPasses('checkIsDeveloper') 


class Checker(object):
  """
  The __setitem__() and __getitem__() methods are overloaded to DTRT
  when adding new access rights, and retrieving them, so use these
  rather then modifying rights directly if so desired.
  """

  MEMBERSHIP = {
    'anyone': 'allow',
    'club_admin': ('checkHasActiveRoleForScope', club_admin_logic),
    'club_member': ('checkHasActiveRoleForScope', club_member_logic),
    'host': ('checkHasDocumentAccess', [host_logic, 'sponsor']),
    'org_admin': ('checkHasDocumentAccess', [org_admin_logic, 'org']),
    'org_mentor': ('checkHasDocumentAccess', [mentor_logic, 'org']),
    'org_student': ('checkHasDocumentAccess', [student_logic, 'org']),
    'user': 'checkIsUser',
    'user_self': ('checkIsUserSelf', 'scope_path'),
    }

  #: the depths of various scopes to other scopes
  # the 0 entries are not used, and are for clarity purposes only
  SCOPE_DEPTH = {
      'site': None,
      'sponsor': (sponsor_logic, {'sponsor': 0}),
      'program': (program_logic, {'sponsor': 1, 'program': 0}),
      'org': (org_logic, {'sponsor': 2, 'program': 1, 'org': 0}),
      }

  def __init__(self, params):
    """Adopts base.rights as rights if base is set.
    """

    base = params.get('rights') if params else None
    self.rights = base.rights if base else {}
    self.id = None
    self.user = None

  def normalizeChecker(self, checker):
    """Normalizes the checker to a pre-defined format.

    The result is guaranteed to be a list of 2-tuples, the first element is a
    checker (iff there is an checker with the specified name), the second
    element is a list of arguments that should be passed to the checker when
    calling it in addition to the standard django_args.
    """

    # Be nice an repack so that it is always a list with tuples
    if isinstance(checker, tuple):
      name, arg = checker
      return (name, (arg if isinstance(arg, list) else [arg]))
    else:
      return (checker, [])

  def __setitem__(self, key, value):
    """Sets a value only if no old value exists.
    """

    oldvalue = self.rights.get(key)
    self.rights[key] = oldvalue if oldvalue else value

  def __getitem__(self, key):
    """Retrieves and normalizes the right checkers.
    """

    return [self.normalizeChecker(i) for i in self.rights.get(key, [])]

  def key(self, checker_name):
    """Returns the key for the specified checker for the current user.
    """

    return "%s.%s" % (self.id, checker_name)

  def put(self, checker_name, value):
    """Puts the result for the specified checker in the cache.
    """

    retention = 30

    memcache_key = self.key(checker_name)
    # pylint: disable-msg=E1101
    memcache.add(memcache_key, value, retention)

  def get(self, checker_name):
    """Retrieves the result for the specified checker from cache.
    """

    memcache_key = self.key(checker_name)
    # pylint: disable-msg=E1101
    return memcache.get(memcache_key)

  def doCheck(self, checker_name, django_args, args):
    """Runs the specified checker with the specified arguments.
    """

    checker = getattr(self, checker_name)
    checker(django_args, *args)

  def doCachedCheck(self, checker_name, django_args, args):
    """Retrieves from cache or runs the specified checker.
    """

    cached = self.get(checker_name)

    if cached is None:
      try:
        self.doCheck(checker_name, django_args, args)
        self.put(checker_name, True)
        return
      except out_of_band.Error, exception:
        self.put(checker_name, exception)
        raise

    if cached is True:
      return

    # re-raise the cached exception
    raise cached

  def check(self, use_cache, checker_name, django_args, args):
    """Runs the checker, optionally using the cache.
    """

    if use_cache:
      self.doCachedCheck(checker_name, django_args, args)
    else:
      self.doCheck(checker_name, django_args, args)

  def setCurrentUser(self, id, user):
    """Sets up everything for the current user.
    """

    self.id = id
    self.user = user

  def checkAccess(self, access_type, django_args):
    """Runs all the defined checks for the specified type.

    Args:
      access_type: the type of request (such as 'list' or 'edit')
      rights: a dictionary containing access check functions
      django_args: a dictionary with django's arguments

    Rights usage:
      The rights dictionary is used to check if the current user is allowed
      to view the page specified. The functions defined in this dictionary
      are always called with the provided django_args dictionary as argument. On any
      request, regardless of what type, the functions in the 'any_access' value
      are called. If the specified type is not in the rights dictionary, all
      the functions in the 'unspecified' value are called. When the specified
      type _is_ in the rights dictionary, all the functions in that access_type's
      value are called.
    """

    use_cache = django_args.get('SIDEBAR_CALLING')

    # Call each access checker
    for checker_name, args in self['any_access']:
      self.check(use_cache, checker_name, django_args, args)

    if access_type not in self.rights:
      # No checks defined, so do the 'generic' checks and bail out
      for checker_name, args in self['unspecified']:
        self.check(use_cache, checker_name, django_args, args)
      return

    for checker_name, args in self[access_type]:
      self.check(use_cache, checker_name, django_args, args)

  def hasMembership(self, roles, django_args):
    """Checks whether the user has access to any of the specified roles.

    Makes use of self.MEMBERSHIP, which defines checkers specific to
    document access, as such this method should only be used when checking
    document access.

    Args:
      roles: a list of roles to check
      django_args: the django args that should be passed to doCheck
    """

    try:
      # we need to check manually, as we must return True!
      self.checkIsDeveloper(django_args)
      return True
    except out_of_band.Error:
      pass

    for role in roles:
      try:
        checker_name, args = self.normalizeChecker(self.MEMBERSHIP[role])
        self.doCheck(checker_name, django_args, args)
        # the check passed, we can stop now
        return True
      except out_of_band.Error:
        continue

    return False

  @allowDeveloper
  def checkMembership(self, action, prefix, status, django_args):
    """Checks whether the user has access to the specified status.

    Args:
      action: the action that was performed (e.g., 'read')
      prefix: the prefix, determines what access set is used
      status: the access status (e.g., 'public')
      django_args: the django args to pass on to the checkers
    """

    checker = rights_logic.Checker(prefix)
    roles = checker.getMembership(status)

    message_fmt = DEF_NEED_MEMBERSHIP_MSG_FMT % {
        'action': action,
        'prefix': prefix,
        'status': status,
        }

    # try to see if they belong to any of the roles, if not, raise an
    # access violation for the specified action, prefix and status.
    if not self.hasMembership(roles, django_args):
      raise out_of_band.AccessViolation(message_fmt)

  def checkHasAny(self, django_args, checks):
    """Checks if any of the checks passes.

    If none of the specified checks passes, the exception that the first of the
    checks raised is reraised.
    """

    first = None

    for checker_name, args in checks:
      try:
        self.doCheck(checker_name, django_args, args)
        # one check passed, all is well
        return
      except out_of_band.Error, exception:
        # store the first exception
        first = first if first else exception

    # none passed, re-raise the first exception
    # pylint: disable-msg=W0706
    raise first

  def allow(self, django_args):
    """Never raises an alternate HTTP response.  (an access no-op, basically).

    Args:
      django_args: a dictionary with django's arguments
    """

    return

  def deny(self, django_args=None):
    """Always raises an alternate HTTP response.

    Args:
      django_args: a dictionary with django's arguments

    Raises:
      always raises AccessViolationResponse if called
    """

    context = django_args.get('context', {})
    context['title'] = 'Access denied'

    raise out_of_band.AccessViolation(DEF_PAGE_DENIED_MSG, context=context)

  def checkIsLoggedIn(self, django_args=None):
    """Raises an alternate HTTP response if Google Account is not logged in.

    Args:
      django_args: a dictionary with django's arguments, not used

    Raises:
      AccessViolationResponse:
      * if no Google Account is even logged in
    """

    if self.id:
      return

    raise out_of_band.LoginRequest()

  def checkNotLoggedIn(self, django_args=None):
    """Raises an alternate HTTP response if Google Account is logged in.

    Args:
      django_args: a dictionary with django's arguments, not used

    Raises:
      AccessViolationResponse:
      * if a Google Account is currently logged in
    """

    if not self.id:
      return

    raise out_of_band.LoginRequest(message_fmt=DEF_LOGOUT_MSG_FMT)

  def checkIsUser(self, django_args=None):
    """Raises an alternate HTTP response if Google Account has no User entity.

    Args:
      django_args: a dictionary with django's arguments, not used

    Raises:
      AccessViolationResponse:
      * if no User exists for the logged-in Google Account, or
      * if no Google Account is logged in at all
      * if User has not agreed to the site-wide ToS, if one exists
    """

    self.checkIsLoggedIn()

    if not self.user:
      raise out_of_band.LoginRequest(message_fmt=DEF_NO_USER_LOGIN_MSG)

    if user_logic.agreesToSiteToS(self.user):
      return

    # Would not reach this point of site-wide ToS did not exist, since
    # agreesToSiteToS() call above always returns True if no ToS is in effect.
    login_msg_fmt = DEF_AGREE_TO_TOS_MSG_FMT % {
        'tos_link': redirects.getToSRedirect(site_logic.getSingleton())}

    raise out_of_band.LoginRequest(message_fmt=login_msg_fmt)

  @allowDeveloper
  def checkIsHost(self, django_args=None):
    """Checks whether the current user has a role entity.

    Args:
      django_args: the keyword args from django, not used
    """

    if not django_args:
      django_args = {}

    return self.checkHasActiveRole(django_args, host_logic)

  @allowDeveloper
  def checkIsUserSelf(self, django_args, field_name):
    """Checks whether the specified user is the logged in user.

    Args:
      django_args: the keyword args from django, only field_name is used
    """

    self.checkIsUser()

    if not field_name in django_args:
      self.deny()

    if self.user.link_id == django_args[field_name]:
      return

    raise out_of_band.AccessViolation(DEF_NOT_YOUR_ENTITY_MSG)

  def checkIsUnusedAccount(self, django_args=None):
    """Raises an alternate HTTP response if Google Account has a User entity.

    Args:
      django_args: a dictionary with django's arguments, not used

    Raises:
      AccessViolationResponse:
      * if a User exists for the logged-in Google Account, or
      * if a User has this Gooogle Account in their formerAccounts list
    """

    self.checkIsLoggedIn()

    fields = {'account': self.id}
    user_entity = user_logic.getForFields(fields, unique=True)

    if not user_entity and not user_logic.isFormerAccount(self.id):
      # this account has not been used yet
      return

    message_fmt = DEF_USER_ACCOUNT_INVALID_MSG_FMT % {
        'email' : self.id.email()
        }

    raise out_of_band.LoginRequest(message_fmt=message_fmt)

  def checkHasUserEntity(self, django_args=None):
    """Raises an alternate HTTP response if Google Account has no User entity.

    Args:
      django_args: a dictionary with django's arguments

    Raises:
      AccessViolationResponse:
      * if no User exists for the logged-in Google Account, or
      * if no Google Account is logged in at all
    """

    self.checkIsLoggedIn()

    if self.user:
      return

    raise out_of_band.LoginRequest(message_fmt=DEF_NO_USER_LOGIN_MSG)

  def checkIsDeveloper(self, django_args=None):
    """Raises an alternate HTTP response if Google Account is not a Developer.

    Args:
      django_args: a dictionary with django's arguments, not used

    Raises:
      AccessViolationResponse:
      * if User is not a Developer, or
      * if no User exists for the logged-in Google Account, or
      * if no Google Account is logged in at all
    """

    self.checkIsUser()

    if user_logic.isDeveloper(account=self.id, user=self.user):
      return

    login_message_fmt = DEF_DEV_LOGOUT_LOGIN_MSG_FMT % {
        'role': 'a Site Developer ',
        }

    raise out_of_band.LoginRequest(message_fmt=login_message_fmt)

  @allowDeveloper
  @denySidebar
  def _checkIsActive(self, django_args, logic, fields):
    """Raises an alternate HTTP response if the entity is not active.

    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
      fields: the name of the fields that should be copied verbatim
              from the django_args as filter

    Raises:
      AccessViolationResponse:
      * if no entity is found
      * if the entity status is not active
    """

    self.checkIsUser()

    fields = dicts.filter(django_args, fields)
    fields['status'] = 'active'

    entity = logic.getForFields(fields, unique=True)

    if entity:
      return entity

    raise out_of_band.AccessViolation(message_fmt=DEF_NO_ACTIVE_ENTITY_MSG)

  def checkGroupIsActiveForScopeAndLinkId(self, django_args, logic):
    """Checks that the specified group is active.

    Only group where both the link_id and the scope_path match the value
    of the link_id and the scope_path from the django_args are considered.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """

    fields = ['scope_path', 'link_id']
    return self._checkIsActive(django_args, logic, fields)

  def checkGroupIsActiveForLinkId(self, django_args, logic):
    """Checks that the specified group is active.

    Only group where the link_id matches the value of the link_id
    from the django_args are considered.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """

    return self._checkIsActive(django_args, logic, ['link_id'])

  def checkHasActiveRole(self, django_args, logic):
    """Checks that the user has the specified active role.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """

    django_args = django_args.copy()
    django_args['user'] = self.user
    return self._checkIsActive(django_args, logic, ['user'])

  def _checkHasActiveRoleFor(self, django_args, logic, field_name):
    """Checks that the user has the specified active role.

    Only roles where the field as specified by field_name matches the
    scope_path from the django_args are considered.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """

    fields = [field_name, 'user']
    django_args = django_args.copy()
    django_args['user'] = self.user
    return self._checkIsActive(django_args, logic, fields)

  def checkHasActiveRoleForKeyFieldsAsScope(self, django_args, logic):
    """Checks that the user has the specified active role.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """

    key_fields = "%(scope_path)s/%(link_id)s" % django_args
    new_args = {'scope_path': key_fields}
    return self._checkHasActiveRoleFor(new_args, logic, 'scope_path')

  def checkHasActiveRoleForScope(self, django_args, logic):
    """Checks that the user has the specified active role.

    Only roles where the scope_path matches the scope_path from the
    django_args are considered.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """

    return self._checkHasActiveRoleFor(django_args, logic, 'scope_path')

  def checkHasActiveRoleForLinkId(self, django_args, logic):
    """Checks that the user has the specified active role.

    Only roles where the link_id matches the link_id from the
    django_args are considered.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """

    return self._checkHasActiveRoleFor(django_args, logic, 'link_id')

  def checkHasActiveRoleForLinkIdAsScope(self, django_args, logic):
    """Checks that the user has the specified active role.

    Only roles where the scope_path matches the link_id from the
    django_args are considered.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """

    django_args = django_args.copy()
    django_args['scope_path'] = django_args['link_id']
    return self._checkHasActiveRoleFor(django_args, logic, 'scope_path')

  def checkHasDocumentAccess(self, django_args, logic, target_scope):
    """Checks that the user has access to the specified document scope.
    
    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to look up the entity
    """
    
    prefix = django_args['prefix']
    if self.SCOPE_DEPTH.get(prefix):
      scope_logic, depths = self.SCOPE_DEPTH[prefix]
    else:
      return self.checkHasActiveRole(django_args, logic)

    depth = depths.get(target_scope, 0)

    # nothing to do
    if not (scope_logic and depth):
      return self.checkHasActiveRoleForScope(django_args, logic)

    # we don't want to modify the original django args
    django_args = django_args.copy()

    entity = scope_logic.getFromKeyName(django_args['scope_path'])

    # cannot have access to the specified scope if it is invalid
    if not entity:
      raise out_of_band.AccessViolation(message_fmt=DEF_NO_ACTIVE_ENTITY_MSG)

    # walk up the scope to where we need to be
    for _ in range(depth):
      entity = entity.scope

    django_args['scope_path'] = entity.key().id_or_name()

    self.checkHasActiveRoleForScope(django_args, logic)

  def checkSeeded(self, django_args, checker_name, *args):
    """Wrapper to update the django_args with the contens of seed first.
    """

    django_args.update(django_args.get('seed', {}))
    self.doCheck(checker_name, django_args, args)

  def checkCanMakeRequestToGroup(self, django_args, group_logic):
    """Raises an alternate HTTP response if the specified group is not in an
    active status.

    Args:
      django_args: a dictionary with django's arguments
      group_logic: Logic module for the type of group which the request is for
    """

    self.checkIsUser(django_args)

    group_entity = role_logic.getGroupEntityFromScopePath(
        group_logic.logic, django_args['scope_path'])

    if not group_entity:
      raise out_of_band.Error(DEF_GROUP_NOT_FOUND_MSG, status=404)

    if group_entity.status != 'active':
      # tell the user that this group is not active
      raise out_of_band.AccessViolation(message_fmt=DEF_NO_ACTIVE_GROUP_MSG)

    return

  def checkCanCreateFromRequest(self, django_args, role_name):
    """Raises an alternate HTTP response if the specified request does not exist
       or if it's status is not group_accepted. Also when the group this request
       is from is in an inactive or invalid status access will be denied.
    
    Args:
      django_args: a dictionary with django's arguments
      role_name: name of the role
    """

    self.checkIsUserSelf(django_args, 'link_id')

    fields = {
        'link_id': django_args['link_id'],
        'scope_path': django_args['scope_path'],
        'role': role_name,
        'status': 'group_accepted',
        }

    entity = request_logic.getForFields(fields, unique=True)
    # pylint: disable-msg=E1103
    if entity and (entity.scope.status not in ['invalid', 'inactive']):
      return

    raise out_of_band.AccessViolation(message_fmt=DEF_NO_REQUEST_MSG)

  def checkIsMyGroupAcceptedRequest(self, django_args):
    """Checks whether the user can accept the specified request.
    
    Args:
      django_args: a dictionary with django's arguments
    """

    self.checkCanCreateFromRequest(django_args, django_args['role'])

  def checkCanProcessRequest(self, django_args, role_name):
    """Raises an alternate HTTP response if the specified request does not exist
       or if it's status is completed or denied. Also Raises an alternate HTTP response
       whenever the group in the request is not active.
       
    Args:
      django_args: a dictionary with django's arguments
      role_name: name of the role
    """

    self.checkIsUser(django_args)

    fields = {
        'link_id': django_args['link_id'],
        'scope_path': django_args['scope_path'],
        'role': role_name,
        }

    request_entity = request_logic.getFromKeyFieldsOr404(fields)

    if request_entity.status in ['completed', 'denied']:
      raise out_of_band.AccessViolation(message_fmt=DEF_REQUEST_COMPLETED_MSG)

    if request_entity.scope.status == 'active':
      return

    raise out_of_band.AccessViolation(message_fmt=DEF_SCOPE_INACTIVE_MSG)

  @allowDeveloper
  @denySidebar
  def checkIsHostForProgram(self, django_args):
    """Checks if the user is a host for the specified program.

    Args:
      django_args: a dictionary with django's arguments
    """

    program = program_logic.getFromKeyFields(django_args)

    if not program or program.status == 'invalid':
      raise out_of_band.AccessViolation(message_fmt=DEF_NO_ACTIVE_PROGRAM_MSG)

    new_args = {'scope_path': program.scope_path }
    self.checkHasActiveRoleForScope(new_args, host_logic)

  @allowDeveloper
  @denySidebar
  def checkIsHostForProgramInScope(self, django_args):
    """Checks if the user is a host for the specified program.

    Args:
      django_args: a dictionary with django's arguments
    """

    scope_path = django_args.get('scope_path')

    if not scope_path:
      raise out_of_band.AccessViolation(message_fmt=DEF_PAGE_DENIED_MSG)

    program = program_logic.getFromKeyName(scope_path)

    if not program or program.status == 'invalid':
      raise out_of_band.AccessViolation(message_fmt=DEF_NO_ACTIVE_PROGRAM_MSG)

    django_args = {'scope_path': program.scope_path}
    self.checkHasActiveRoleForScope(django_args, host_logic)

  @allowDeveloper
  @denySidebar
  def checkIsActivePeriod(self, django_args, period_name, key_name_arg):
    """Checks if the given period is active for the given program.

    Args:
      django_args: a dictionary with django's arguments
      period_name: the name of the period which is checked
      key_name_arg: the entry in django_args that specifies the given program
        keyname. If none is given the key_name is constructed from django_args
        itself.

    Raises:
      AccessViolationResponse:
      * if no active Program is found
      * if the period is not active
    """

    if key_name_arg and key_name_arg in django_args:
      key_name = django_args[key_name_arg]
    else:
      key_name = program_logic.getKeyNameFromFields(django_args)

    program_entity = program_logic.getFromKeyName(key_name)

    if not program_entity or (
        program_entity.status in ['inactive', 'invalid']):
      raise out_of_band.AccessViolation(message_fmt=DEF_SCOPE_INACTIVE_MSG)

    if timeline_helper.isActivePeriod(program_entity.timeline, period_name):
      return

    raise out_of_band.AccessViolation(message_fmt=DEF_PAGE_INACTIVE_MSG)

  @allowDeveloper
  @denySidebar
  def checkIsAfterEvent(self, django_args, event_name, key_name_arg):
    """Checks if the given event has taken place for the given program.

    Args:
      django_args: a dictionary with django's arguments
      event_name: the name of the event which is checked
      key_name_arg: the entry in django_args that specifies the given program
        keyname. If none is given the key_name is constructed from django_args
        itself.

    Raises:
      AccessViolationResponse:
      * if no active Program is found
      * if the event has not taken place yet
    """

    if key_name_arg and key_name_arg in django_args:
      key_name = django_args[key_name_arg]
    else:
      key_name = program_logic.getKeyNameFromFields(django_args)

    program_entity = program_logic.getFromKeyName(key_name)

    if not program_entity or (
        program_entity.status in ['inactive', 'invalid']):
      raise out_of_band.AccessViolation(message_fmt=DEF_SCOPE_INACTIVE_MSG)

    if timeline_helper.isAfterEvent(program_entity.timeline, event_name):
      return

    raise out_of_band.AccessViolation(message_fmt=DEF_PAGE_INACTIVE_MSG)

  def checkCanCreateOrgApp(self, django_args, period_name):
    """Checks to see if the program in the scope_path is accepting org apps
    
    Args:
      django_args: a dictionary with django's arguments
      period_name: the name of the period which is checked
    """

    if 'seed' in django_args:
      return self.checkIsActivePeriod(django_args['seed'],
          period_name, 'scope_path')
    else:
      return

  @allowDeveloper
  def checkCanEditGroupApp(self, django_args, group_app_logic):
    """Checks if the group_app in args is valid to be edited by 
       the current user.

    Args:
      django_args: a dictionary with django's arguments
      group_app_logic: A logic instance for the Group Application
    """

    self.checkIsUser(django_args)

    fields = {
        'link_id': django_args['link_id'],
        'applicant': self.user,
        'status' : ['needs review', 'rejected']
        }

    if 'scope_path' in django_args:
      fields['scope_path'] = django_args['scope_path']

    entity = group_app_logic.getForFields(fields)

    if entity:
      return

    del fields['applicant']
    fields['backup_admin'] = self.user

    entity = group_app_logic.getForFields(fields)

    if entity:
      return

    raise out_of_band.AccessViolation(message_fmt=DEF_NOT_YOUR_ENTITY_MSG)

  @allowSidebar
  def checkCanReviewGroupApp(self, django_args, group_app_logic):
    """Checks if the group_app in args is valid to be reviewed.

    Args:
      django_args: a dictionary with django's arguments
      group_app_logic: A logic instance for the Group Application
    """

    if 'link_id' not in django_args:
      # calling review overview, so we can't check a specified entity
      return

    fields = {
        'link_id': django_args['link_id'],
        'status': ['needs review', 'accepted', 'rejected', 'ignored',
            'pre-accepted', 'pre-rejected']
        }

    if 'scope_path' in django_args:
      fields['scope_path'] = django_args['scope_path']

    entity = group_app_logic.getForFields(fields)

    if entity:
      return

    raise out_of_band.AccessViolation(message_fmt=DEF_REVIEW_COMPLETED_MSG)

  @allowDeveloper
  def checkIsApplicationAccepted(self, django_args, app_logic):
    """Returns an alternate HTTP response if Google Account has no accepted
       Group Application entity for the specified arguments.

    Args:
      django_args: a dictionary with django's arguments

     Raises:
       AccessViolationResponse: if the required authorization is not met

    Returns:
      None if the Accepted Group App exists for the specified program, or a subclass
      of django.http.HttpResponse which contains the alternate response
      should be returned by the calling view.
    """

    self.checkIsUser(django_args)

    application = app_logic.getFromKeyFieldsOr404(django_args)
    applicant = application.applicant.key()
    backup_admin = application.backup_admin
    backup_admin = backup_admin.key() if backup_admin else None
    user = self.user.key()

    # check if the application is accepted and the applicant is the current user
    if application.status == 'accepted' and (applicant == user or
                                             backup_admin == user):
      return

    raise out_of_band.AccessViolation(message_fmt=DEF_NO_APPLICATION_MSG)

  def checkIsNotParticipatingInProgramInScope(self, django_args):
    """Checks if the current user has no roles for the given 
       program in django_args.

    Args:
      django_args: a dictionary with django's arguments

     Raises:
       AccessViolationResponse: if the current user has a student, mentor or
                                org admin role for the given program.
    """

    if not django_args.get('scope_path'):
      raise out_of_band.AccessViolation(message_fmt=DEF_PAGE_DENIED_MSG)

    program_entity = program_logic.getFromKeyNameOr404(
        django_args['scope_path'])
    user_entity = user_logic.getForCurrentAccount()

    filter = {'user': user_entity,
              'scope': program_entity,
              'status': 'active'}

    # check if the current user is already a student for this program
    student_role = student_logic.getForFields(filter, unique=True)

    if student_role:
      raise out_of_band.AccessViolation(
          message_fmt=DEF_ALREADY_PARTICIPATING_MSG)

    # fill the role_list with all the mentor and org admin roles for this user
    # role_list = []

    filter = {'user': user_entity,
              'program': program_entity,
              'status': 'active'}

    mentor_role = mentor_logic.getForFields(filter, unique=True)
    if mentor_role:
      # the current user has a role for the given program
      raise out_of_band.AccessViolation(
            message_fmt=DEF_ALREADY_PARTICIPATING_MSG)

    org_admin_role = org_admin_logic.getForFields(filter, unique=True)
    if org_admin_role:
      # the current user has a role for the given program
      raise out_of_band.AccessViolation(
            message_fmt=DEF_ALREADY_PARTICIPATING_MSG)

    # no roles found, access granted
    return

  def checkIsNotStudentForProgramInScope(self, django_args):
    """Checks if the current user is not a student for the given
       program in django_args.

    Args:
      django_args: a dictionary with django's arguments

     Raises:
       AccessViolationResponse: if the current user has a student
                                role for the given program.
    """

    if django_args.get('seed'):
      key_name = django_args['seed']['scope_path']
    else:
      key_name = django_args['scope_path']

    program_entity = program_logic.getFromKeyNameOr404(key_name)
    user_entity = user_logic.getForCurrentAccount()

    filter = {'user': user_entity,
              'scope': program_entity,
              'status': 'active'}

    # check if the current user is already a student for this program
    student_role = student_logic.getForFields(filter, unique=True)

    if student_role:
      raise out_of_band.AccessViolation(
          message_fmt=DEF_ALREADY_STUDENT_ROLE_MSG)

    return

  def checkIsNotStudentForProgramOfOrg(self, django_args):
    """Checks if the current user has no active Student role for the program
       that the organization in the scope_path is participating in.

    Args:
      django_args: a dictionary with django's arguments

     Raises:
       AccessViolationResponse: if the current user is a student for the
                                program the organization is in.
    """

    if not django_args.get('scope_path'):
      raise out_of_band.AccessViolation(message_fmt=DEF_PAGE_DENIED_MSG)

    org_entity = org_logic.getFromKeyNameOr404(django_args['scope_path'])
    user_entity = user_logic.getForCurrentAccount()

    filter = {'scope': org_entity.scope,
              'user': user_entity,
              'status': 'active'}

    student_role = student_logic.getForFields(filter=filter, unique=True)

    if student_role:
      raise out_of_band.AccessViolation(
          message_fmt=DEF_ALREADY_STUDENT_ROLE_MSG)

    return

  @allowDeveloper
  def checkRoleAndStatusForStudentProposal(self, django_args, allowed_roles,
                                           role_status, proposal_status):
    """Checks if the current user has access to the given proposal.

    Args:
      django_args: a dictionary with django's arguments
      allowed_roles: list with names for the roles allowed to pass access check
      role_status: list with states allowed for the role
      proposal_status: a list with states allowed for the proposal

     Raises:
       AccessViolationResponse:
         - If there is no proposal found
         - If the proposal is not in one of the required states.
         - If the user does not have any ofe the required roles
    """

    self.checkIsUser(django_args)

    # bail out with 404 if no proposal is found
    proposal_entity = student_proposal_logic.getFromKeyFieldsOr404(django_args)

    if not proposal_entity.status in proposal_status:
      # this proposal can not be accessed at the moment
      raise out_of_band.AccessViolation(
          message_fmt=DEF_NO_ACTIVE_ENTITY_MSG)

    user_entity = self.user

    if 'proposer' in allowed_roles:
      # check if this proposal belongs to the current user
      student_entity = proposal_entity.scope
      if (user_entity.key() == student_entity.user.key()) and (
          student_entity.status in role_status):
        return

    filter = {'user': user_entity,
        'status': role_status}

    if 'host' in allowed_roles:
      # check if the current user is a host for this proposal's program
      filter['scope'] =  proposal_entity.program

      if host_logic.getForFields(filter, unique=True):
        return

    if 'org_admin' in allowed_roles:
      # check if the current user is an admin for this proposal's org
      filter['scope'] = proposal_entity.org

      if org_admin_logic.getForFields(filter, unique=True):
        return

    if 'mentor' in allowed_roles:
      # check if the current user is a mentor for this proposal's org
      filter['scope'] = proposal_entity.org

      if mentor_logic.getForFields(filter, unique=True):
        return

    # no roles found, access denied
    raise out_of_band.AccessViolation(
        message_fmt=DEF_NEED_ROLE_MSG)

  @allowDeveloper
  def checkCanStudentPropose(self, django_args, key_location, check_limit):
    """Checks if the program for this student accepts proposals.

    Args:
      django_args: a dictionary with django's arguments
      key_location: the key for django_args in which the key_name
                    from the student is stored
      check_limit: iff true checks if the student reached the apps_tasks_limit
                   for the given program.
    """

    self.checkIsUser(django_args)

    if django_args.get('seed'):
      key_name = django_args['seed'][key_location]
    else:
      key_name = django_args[key_location]

    student_entity = student_logic.getFromKeyName(key_name)

    if not student_entity or student_entity.status == 'invalid':
      raise out_of_band.AccessViolation(
        message_fmt=DEF_SIGN_UP_AS_STUDENT_MSG)

    program_entity = student_entity.scope

    if not timeline_helper.isActivePeriod(program_entity.timeline,
                                          'student_signup'):
      raise out_of_band.AccessViolation(message_fmt=DEF_PAGE_INACTIVE_MSG)

    if check_limit:
      # count all studentproposals by the student
      fields = {'scope': student_entity}
      proposal_query = student_proposal_logic.getQueryForFields(fields)

      if proposal_query.count() >= program_entity.apps_tasks_limit:
        # too many proposals access denied
        raise out_of_band.AccessViolation(message_fmt=DEF_MAX_PROPOSALS_REACHED)

    return

  @allowDeveloper
  def checkIsStudent(self, django_args, key_location, status):
    """Checks if the current user is the given student.

    Args:
      django_args: a dictionary with django's arguments
      key_location: the key for django_args in which the key_name
                    from the student is stored
      status: the allowed status for the student
    """

    self.checkIsUser(django_args)

    if 'seed' in django_args:
      key_name = django_args['seed'][key_location]
    else:
      key_name = django_args[key_location]

    student_entity = student_logic.getFromKeyName(key_name)

    if not student_entity or student_entity.status not in status:
      raise out_of_band.AccessViolation(
        message_fmt=DEF_SIGN_UP_AS_STUDENT_MSG)

    if student_entity.user.key() != self.user.key():
      # this is not the page for the current user
      self.deny(django_args)

    return

  @allowDeveloper
  def checkIsMyStudentProject(self, django_args):
    """Checks whether the project belongs to the current user.

    Args:
      django_args: a dictionary with django's arguments

     Raises:
       AccessViolationResponse:
         - If there is no project found
         - If the project does not belong to the current user
    """

    self.checkIsUser()

    project_entity = student_project_logic.getFromKeyFieldsOr404(django_args)

    if project_entity.student.user.key() != self.user.key():
      raise out_of_band.AccessViolation(
          message_fmt=DEF_NOT_YOUR_ENTITY_MSG)

    return

  @allowDeveloper
  def checkIsHostForStudentProject(self, django_args):
    """Checks whether the user is Host for the specified project.

    Args:
      django_args: a dictionary with django's arguments

     Raises:
       AccessViolationResponse:
         - If there is no project found
         - If the user is not a host for hte specified project
    """

    self.checkIsUser()

    project_entity = student_project_logic.getFromKeyFieldsOr404(django_args)
    program_entity = project_entity.program

    new_args = {'scope_path': program_entity.scope_path }
    self.checkHasActiveRoleForScope(new_args, host_logic)

    return

  @allowDeveloper
  def checkStudentProjectHasStatus(self, django_args, allowed_status):
    """Checks whether the Project has one of the given statuses.

    Args:
      django_args: a dictionary with django's arguments
      allowed_status: list with the allowed statusses for the entity

     Raises:
       AccessViolationResponse:
         - If there is no project found
         - If the project is not in the requested status
    """

    project_entity = student_project_logic.getFromKeyFieldsOr404(django_args)

    if not project_entity.status in allowed_status:
      raise out_of_band.AccessViolation(
          message_fmt=DEF_NO_ACTIVE_ENTITY_MSG)

    return

  @allowDeveloper
  def checkIsMyEntity(self, django_args, logic,
                      field_name='user', user=False):
    """Checks whether the entity belongs to the user.

    Args:
      django_args: a dictionary with django's arguments
      logic: the logic that should be used to fetch the entity
      field_name: the name of the field the entity uses to store it's owner
      user: true iff the entity stores the user's reference, false iff keyname
    """

    self.checkIsUser(django_args)

    fields = {
        'link_id': django_args['link_id'],
        field_name: self.user if user else self.user.key().id_or_name()
        }

    if 'scope_path' in django_args:
      fields['scope_path'] = django_args['scope_path']

    entity = logic.getForFields(fields)

    if entity:
      return

    raise out_of_band.AccessViolation(message_fmt=DEF_NOT_YOUR_ENTITY_MSG)

  @allowDeveloper
  @denySidebar
  def checkIsAllowedToManageRole(self, django_args, logic_for_role, 
      manage_role_logic):
    """Returns an alternate HTTP response if the user is not allowed to manage
       the role given in args.

     Args:
       django_args: a dictionary with django's arguments
       logic_for_role: determines the logic for the role in args.
       manage_role_logic: determines the logic for the role which is allowed
           to manage this role.

     Raises:
       AccessViolationResponse: if the required authorization is not met

    Returns:
      None if the given role is active and belongs to the current user.
      None if the current User has an active role (from manage_role_logic)
           that belongs to the same scope as the role that needs to be managed
    """

    try:
      # check if it is the user's own role
      self.checkHasActiveRoleForScope(django_args, logic_for_role)
      self.checkIsMyEntity(django_args, logic_for_role, 'user', True)
      return
    except out_of_band.Error:
      pass

    # apparently it's not the user's role so check 
    # if managing this role is allowed
    fields = {
        'link_id': django_args['link_id'],
        'scope_path': django_args['scope_path'],
        }

    role_entity = logic_for_role.getFromKeyFieldsOr404(fields)

    if role_entity.status != 'active':
      raise out_of_band.AccessViolation(message_fmt=DEF_NO_ACTIVE_ROLE_MSG)

    fields = {
        'link_id': self.user.link_id,
        'scope_path': django_args['scope_path'],
        'status': 'active'
        }

    manage_entity = manage_role_logic.getForFields(fields, unique=True)

    if not manage_entity:
      raise out_of_band.AccessViolation(message_fmt=DEF_NOT_YOUR_ENTITY_MSG)

    return

  @allowSidebar
  @allowDeveloper
  def checkIsSurveyReadable(self, django_args, survey_logic,
                            key_name_field=None):
    """Checks whether a survey is readable.

    Args:
      django_args: a dictionary with django's arguments
      key_name_field: key name field
    """

    if key_name_field:
      key_name = django_args[key_name_field]
      survey = survey_logic.getFromKeyNameOr404(key_name)
    else:
      survey = survey_logic.getFromKeyFieldsOr404(django_args)

    self.checkMembership('read', survey.prefix,
                         survey.read_access, django_args)

  @denySidebar
  @allowDeveloper
  def checkIsMySurveyRecord(self, django_args, survey_logic, id_field):
    """Checks if the SurveyRecord given in the GET arguments as id_field is
    from the current user.

    Args:
      django_args: a dictionary with django's arguments
      survey_logic: Survey Logic which contains the needed Record logic
      id_field: name of the field in the GET dictionary that contains the Record ID.

    Raises:
      AccesViolation if:
        - There is no valid numeric record ID present in the GET dict
        - There is no SurveyRecord with the found ID
        - The SurveyRecord has not been taken by the current user
    """

    self.checkIsUser(django_args)
    user_entity = self.user

    get_dict = django_args['GET']
    record_id = get_dict.get(id_field)

    if not record_id or not record_id.isdigit():
      raise out_of_band.AccessViolation(
          message_fmt=DEF_NO_VALID_RECORD_ID)
    else:
      record_id = int(record_id)

    record_logic = survey_logic.getRecordLogic()
    record_entity = record_logic.getFromIDOr404(record_id)

    if record_entity.user.key() != user_entity.key():
      raise out_of_band.AccessViolation(
          message_fmt=DEF_NOT_YOUR_RECORD)

  @denySidebar
  @allowDeveloper
  def checkIsSurveyWritable(self, django_args, survey_logic,
                            key_name_field=None):
    """Checks whether a survey is writable.

    Args:
      django_args: a dictionary with django's arguments
      key_name_field: key name field
    """

    if key_name_field:
      key_name = django_args[key_name_field]
      survey = survey_logic.getFromKeyNameOr404(key_name)
    else:
      survey = survey_logic.getFromKeyFieldsOr404(django_args)

    self.checkMembership('write', survey.prefix,
                         survey.write_access, django_args)

  @denySidebar
  @allowDeveloper
  def checkIsSurveyTakeable(self, django_args, survey_logic, check_time=True):
    """Checks if the survey specified in django_args can be taken.

    Uses survey.taking_access to map that string onto a check. Also checks for
    survey start and end.

    If the prefix is 'program', the scope of the survey is the program and
    the taking_acccess attribute means:
      mentor: user is mentor for the program
      org_admin: user is org_admin for the program
      student: user is student for the program
      user: valid user on the website

    Args:
      survey_logic: SurveyLogic instance (or subclass)
      check_time: iff True checks if the current date is between the survey
        start and end date.
    """

    if django_args['prefix'] != 'program':
      # TODO: update when generic surveys are allowed
      return self.deny(django_args)

    # get the survey from django_args
    survey = survey_logic.getFromKeyFieldsOr404(django_args)

    # check if the survey can be taken now
    if check_time and not timeline_helper.isActivePeriod(survey, 'survey'):
      raise out_of_band.AccessViolation(message_fmt=DEF_PAGE_INACTIVE_MSG)

    # retrieve the role that is allowed to take this survey
    role = survey.taking_access

    if role == 'user':
      # check if the current user is registered
      return self.checkIsUser(django_args)

    django_args = django_args.copy()

    # get the survey scope
    survey_scope = survey_logic.getScope(survey)

    if role == 'mentor':
      # check if the current user is a mentor for the program in survey.scope
      django_args['program'] = survey_scope
      # program is the 'program' attribute for mentors and org_admins
      return self._checkHasActiveRoleFor(django_args, mentor_logic, 'program')

    if role == 'org_admin':
      # check if the current user is a mentor for the program in survey.scope
      django_args['program'] = survey_scope
      # program is the 'program' attribute for mentors and org_admins
      return self._checkHasActiveRoleFor(django_args, org_admin_logic,
                                         'program')

    if role == 'student':
      # check if the current user is a student for the program in survey.scope
      django_args['scope'] = survey_scope
      # program is the 'scope' attribute for students
      return self.checkHasActiveRoleForScope(django_args, student_logic)

    # unknown role
    self.deny(django_args)

  @denySidebar
  @allowDeveloper
  def checkIsAllowedToTakeProjectSurveyAs(self, django_args, survey_logic,
                                          role_name, project_key_location):
    """Checks whether a ProjectSurvey can be taken by the current User.

    role_name argument determines wether the current user is taking the survey
    as a student or mentor specified by the project in GET dict.

    If the survey is taken as a mentor, org admins for the Organization in
    which the project resides will also have access.

    However if the project entry is not present in the dictionary this access
    check passes.

    Args:
      django_args: a dictionary with django's arguments
      survey_logic: instance of ProjectSurveyLogic (or subclass)
      role_name: String containing either "student" or "mentor"
      project_key_location: String containing the key entry in the GET dict
        where the key for the project can be located.
    """

    if not role_name in ['mentor', 'student']:
      raise InvalidArgumentError('role_name is not mentor or student')

    # check if the current user is signed up
    self.checkIsUser(django_args)
    user_entity = self.user

    # get the project keyname from the GET dictionary
    get_dict = django_args['GET']
    key_name = get_dict.get(project_key_location)

    if not key_name:
      # no key name present so no need to deny access
      return

    # retrieve the Student Project for the key
    project_entity = student_project_logic.getFromKeyNameOr404(key_name)

    # check if a survey can be conducted about this project
    if project_entity.status != 'accepted':
      raise out_of_band.AccessViolation(
          message_fmt=DEF_NOT_ALLOWED_PROJECT_FOR_SURVEY_MSG)

    # get the correct role depending on the role_name
    if role_name == 'student':
      role_entity = project_entity.student
    elif role_name == 'mentor':
      role_entity = project_entity.mentor

    # check if the role matches the current user
    if role_entity.user.key() != user_entity.key() and (
        role_entity.status == 'active'):
      if role_name == 'student':
        raise out_of_band.AccessViolation(
            message_fmt=DEF_NOT_ALLOWED_PROJECT_FOR_SURVEY_MSG)
      elif role_name == 'mentor':
        # check if the current user is an Org Admin for this Student Project
        fields = {'user': user_entity,
                  'scope': project_entity.scope,
                  'status': 'active'}
        admin_entity = org_admin_logic.getForFields(fields, unique=True)
        if not admin_entity:
          # this user is no Org Admin or Mentor for this project
          raise out_of_band.AccessViolation(
              message_fmt=DEF_NOT_ALLOWED_PROJECT_FOR_SURVEY_MSG)
    elif role_entity.status != 'active':
      # this role is not active
      raise out_of_band.AccessViolation(message_fmt=DEF_NEED_ROLE_MSG)

    return

  @denySidebar
  @allowDeveloper
  def checkIsAllowedToViewProjectSurveyRecordAs(
      self, django_args, survey_logic, role_name, record_key_location):
    """Checks wether the current user is allowed to view the record given in
    the GET data by the record_key_location.

    Args:
      django_args: a dictionary with django's arguments
      survey_logic: Survey Logic instance that belongs to the SurveyRecord
        type in question
      role_name: string containing either "student" or "mentor". Determines
        which of the roles the within the project the current user should have
        to view the evaluation results.
      record_key_location: string containing the name of the GET param which
        contains the id for the SurveyRecord to retrieve

    Raises:
      AccessViolation if:
        - No valid numeric Record ID is given in the POST data.
        - No Record could be retrieved for the given Record ID.
        - The current user has not taken the survey, is not the Student/Mentor
          (depending on the role_name) and is not an Org Admin for the project
          to which the SurveyRecord belongs.
    """

    if not role_name in ['mentor', 'student']:
      raise InvalidArgumentError('role_name is not mentor or student')

    self.checkIsUser(django_args)
    user_entity = self.user

    get_dict = django_args['GET']
    record_id = get_dict.get(record_key_location)

    if not record_id or not record_id.isdigit():
      raise out_of_band.AccessViolation(
          message_fmt=DEF_NO_VALID_RECORD_ID)
    else:
      record_id = int(record_id)

    record_logic = survey_logic.getRecordLogic()
    record_entity = record_logic.getFromIDOr404(record_id)

    if record_entity.user.key() == user_entity.key():
      # this record belongs to the current user
      return

    if role_name == 'student':
      role_entity = record_entity.project.student
    elif role_name == 'mentor':
      role_entity = record_entity.project.mentor

    if role_entity.user.key() == user_entity.key() and (
        role_entity.status == 'active'):
      # this user has the role required
      return

    fields = {'user': user_entity,
              'scope': record_entity.org,
              'status': 'active'}
    admin_entity = org_admin_logic.getForFields(fields, unique=True)

    if admin_entity:
      # this user is org admin for the retrieved record's project
      return

    # The current user is no Org Admin, has not taken the Survey and is not
    # the one responsible for taking this survey.
    raise out_of_band.AccessViolation(message_fmt=DEF_NOT_YOUR_RECORD)

  @allowSidebar
  @allowDeveloper
  def checkIsDocumentReadable(self, django_args, key_name_field=None):
    """Checks whether a document is readable by the current user.

    Args:
      django_args: a dictionary with django's arguments
      key_name_field: key name field
    """

    if key_name_field:
      key_name = django_args[key_name_field]
      document = document_logic.getFromKeyNameOr404(key_name)
    else:
      document = document_logic.getFromKeyFieldsOr404(django_args)

    self.checkMembership('read', document.prefix,
                         document.read_access, django_args)

  @denySidebar
  @allowDeveloper
  def checkIsDocumentWritable(self, django_args, key_name_field=None):
    """Checks whether a document is writable by the current user.

    Args:
      django_args: a dictionary with django's arguments
      key_name_field: key name field
    """

    if key_name_field:
      key_name = django_args[key_name_field]
      document = document_logic.getFromKeyNameOr404(key_name)
    else:
      document = document_logic.getFromKeyFieldsOr404(django_args)

    self.checkMembership('write', document.prefix,
                         document.write_access, django_args)

  @denySidebar
  @allowDeveloper
  def checkDocumentList(self, django_args):
    """Checks whether the user is allowed to list documents.
    
    Args:
      django_args: a dictionary with django's arguments
    """

    filter = django_args['filter']
    prefix = filter['prefix']

    checker = rights_logic.Checker(prefix)
    roles = checker.getMembership('list')

    if not self.hasMembership(roles, filter):
      raise out_of_band.AccessViolation(message_fmt=DEF_NO_LIST_ACCESS_MSG)

  @denySidebar
  @allowDeveloper
  def checkDocumentPick(self, django_args):
    """Checks whether the user has access to the specified pick url.

    Will update the 'read_access' field of django_args['GET'].
    
    Args:
      django_args: a dictionary with django's arguments
    """

    get_args = django_args['GET']
    # make mutable in order to inject the proper read_access filter
    mutable = get_args._mutable
    get_args._mutable = True

    if 'prefix' not in get_args:
      raise out_of_band.AccessViolation(message_fmt=DEF_PREFIX_NOT_IN_ARGS_MSG)

    prefix = get_args['prefix']
    django_args['prefix'] = prefix
    django_args['scope_path'] = get_args['scope_path']

    checker = rights_logic.Checker(prefix)
    memberships = checker.getMemberships()

    roles = []
    for key, value in memberships.iteritems():
      if self.hasMembership(value, django_args):
        roles.append(key)

    if not roles:
      roles = ['deny']

    get_args.setlist('read_access', roles)
    get_args._mutable = mutable

  def checkCanEditTimeline(self, django_args):
    """Checks whether this program's timeline may be edited.

    Args:
      django_args: a dictionary with django's arguments
    """
    
    time_line_keyname = timeline_logic.getKeyFieldsFromFields(django_args)
    timeline_entity = timeline_logic.getFromKeyName(time_line_keyname)

    if not timeline_entity:
      # timeline does not exists so deny
      self.deny(django_args)

    fields = program_logic.getKeyFieldsFromFields(django_args)
    self.checkIsHostForProgram(fields)
