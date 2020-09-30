.. _howto/rdtraining/E_unittest:

=============================
Advanced E: Python Unit Tests
=============================

.. tip:: This tutorial assumes you followed the Core Training.

  To do the exercise, fetch the branch 14.0-core from the repository XXX.
  It contains a basic module we will use as a starting point


**Reference**:
`Odoo's Test Framework: Learn Best Practices <https://www.youtube.com/watch?v=JEIscps0OOQ>`__
(Odoo Experience 2020) on Youtube.

Writing tests is a necessity for multiple reasons. Here is a non exhaustive list:

* Ensure it will not be broken in the future
* Define the scope of your code
* Give examples of use cases
* It is one way to technically document the code
* Help you develop by defining your goal before working towards it

Integration Bots
================

.. note:: This section is only for Odoo employees and people that are contributing to
  `github.com/odoo`. We highly recommend having your own CI if it is not the case.

The tests would be useless without a Continuous Integration (CI). This is why we have some bots
running all the tests at different moments. Whether you are working at Odoo or not, if you are
trying to merge something inside `odoo/odoo`, `odoo/enterprise`, `odoo/upgrade` or on odoo.sh, you
will have to go through the CI. If you are working on another project, you should think of adding
your own CI.

Runbot
------

**Reference**: the documentation related to this topic can be found in
`Runbot FAQ <https://runbot.odoo.com/doc>`__.

Most of the tests are run on `Runbot <https://runbot.odoo.com>`__ every time a commit is pushed on
GitHub.

You can see the state of a commit/branch by filtering on the runbot dashboard.

A **bundle** is created for each branch. A bundle consists of a configuration and contains the
batches.

A **batch** is a set of builds, depending on the parameters of the bundle.
A batch is greened if all the builds are greened.

A **build** is when we launch a server. It can be divided in sub-builds. Usually there are builds
for the community version, the enterprise version (only if there is an enterprise branch but you
can force the build), and the migration of the branch.
A build is greened if every sub-build is greened.

A **sub-build** only does some parts of what a full build does. It is used to speed up the CI
process. Generally it is used to split the post install tests in 4 parallel instances.
A sub-build is greened if all the tests are passing and there are no errors/warnings logged.

.. note::
  * Robodoo doesn't care what the changes were. It will always run the same tests, meaning it
    will install all the modules. This means something might not work if runbot greened but your
    changes depend on something you don't depend on.
  * The localization modules are not installed on runbot (except the generic one), some modules
    with external dependencies can be excluded also.
  * There is a nightly build running additional tests, like module operations, localization, single
    module installs, multi-builds for nondeterministic bugs, etc.
    These are not kept in the standard CI to shorten the time of execution.

You can also login on a build built by runbot. There are 3 users usable: `admin`, `demo` and
`portal`. The password is the same as the login. This is useful to quickly test things on different
versions without having to build it locally. The full logs are also available; these are used for
monitoring.

Robodoo
-------

You will most likely have to gain a little bit more experience before having the rights to summon
robodoo, but here are a few remarks anyways.

Robodoo is the guy spamming the CI status as tags on your PRs, but he is also the guy that kindly
integrates your commits on the main repositories.

When the last batch is greened, the reviewer can ask robodoo to merge your PR (actually it is more
a `rebase` than a `merge`). It will then go to the mergebot.


Mergebot
--------

`Mergebot <https://mergebot.odoo.com>`__ is the last testing phase before merging a PR.

It will take the commits in your branch not yet present on the target, stage it and rerun the tests
one more time, including the enterprise version even if you are only changing something in
community.

Modules
=======

Because Odoo is modular, the tests need to be modular also. This means the modules are defined in
the module that adds the functionality you add; and that tests cannot depend on functionality
coming from modules your module doesn't depend on.

If the behavior you want to test can be changed by the installation of another module, you need to
ensure that the tag `at_install` is set; otherwise you can use the tag `post_install` to speed up
the CI, and ensure it is not changed if it shouldn't.

Writing a test
==============

**Reference**: the documentation related to this topic can be found in
`Python unittest <https://docs.python.org/3/library/unittest.html>`__.

**Reference**: the documentation related to this topic can be found in
:ref:`Testing Odoo<reference/testing>`.

Here are a few things to take into consideration before writing a test

* The tests should be independent from the data currently in the database
* Tests should not impact the database by leaving/changing residual data. This is usually done by
  the test framework
* For a bug fix, the test should fail before applying the fix and pass after.
* Don't test something that is already tested elsewhere; you can trust the ORM. Most of the tests
  in business modules should only test the business flows.
* You shouldn't need to flush data into the database.

.. note:: Remember that ``onchange`` only applies in the Form views, not by changing the attributes
  in python. This also applies in the tests. If you want to emulate a Form view, you can use
  ``odoo.tests.common.Form``.

The tests should be located in a ``tests`` folder in the root of your module. Each test file name
should start with `test_` and be imported in the ``__init__.py`` of the test folder. You shouldn't
import the test folder/module in the ``__init__.py`` of the module.

.. code-block:: bash

  estate
  ├── models
  │   ├── *.py
  │   └── __init__.py
  ├── tests
  │   ├── test_*.py
  │   └── __init__.py
  ├── __init__.py
  └── __manifest__.py

.. note:: Some older tests are extending ``odoo.tests.common.TransactionCase``, but they are less
  scalable. The difference is that the setup is done per test method and not per test class.
  The data changed are rollbacked between each test in `SavepointCase` to have the same behavior as
  in `TransactionCase`.

All the tests should extend ``odoo.tests.common.SavepointCase``. You usually define a
``setUpClass``, and the tests. After doing the `setUpClass`, you have an `env` available on the
class and can start interacting with the ORM.

These test classes are build on top of the ``unittest`` module.

.. code-block:: python

  from odoo.tests.common import SavepointCase
  from odoo.exceptions import UserError

  # The CI will run these tests after all the modules are installed,
  # not right after installing the one defining it.
  @tagged('post_install', '-at_install')
  class EstateTestCase(SavepointCase):

      @classmethod
      def setUpClass(cls):
          # add env on cls and many other things
          super(EstateTestCase, cls).setUpClass()

          # create the data for each tests. By doing it in the setUpClass instead
          # of in a setUp or in each test case, we reduce the testing time and
          # the duplication of code.
          cls.properties = cls.env['estate.property'].create([...])

      def test_creation_area(self):
          """Test that the total_area is computed like it should."""
          self.properties.living_area = 20
          self.assertRecordValues(self.properties, [
             {'name': ..., 'total_area': ...},
             {'name': ..., 'total_area': ...},
          ])


      def test_action_sell(self):
          """Test that everything behaves like it should when selling a property."""
          self.properties.action_sold()
          self.assertRecordValues(self.properties, [
             {'name': ..., 'state': ...},
             {'name': ..., 'state': ...},
          ])

          with self.assertRaises(UserError):
              self.properties.forbidden_action_on_sold_property()

.. note:: For more readability, split your tests into multiple files depending on the scope of the
  tests. You can also have a Common class that most of the tests should inherit from; that common
  class can define the whole set up for the module. For instance in
  `account <https://github.com/odoo/odoo/blob/14.0/addons/account/tests/common.py>`__.

.. exercise:: Ensure no one can create an offer for a sold Property, and create a test for it.


.. exercise:: Someone keeps breaking the reset of Garden Area and Orientation when you uncheck the
  Garden checkbox. Make sure it doesn't happen again.

  .. tip:: Tip: remember the note about `Form` a little bit above.
