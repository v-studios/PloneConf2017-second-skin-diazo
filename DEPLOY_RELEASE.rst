=====================
 TTT: Deployment SOP
=====================

---------------------------------------------------------
(or: how i stopped worrying and learned to cut a release)
---------------------------------------------------------


From git Git-Flow cheat sheet : http://danielkummer.github.io/git-flow-cheatsheet/#release

Create Release
==============

To create a release from the v-studios/tttdiazo repo, use the
following commands::

  git flow release start <release name> [<commit id>]

* creates a new branch from develop called “release/<release name>”,
  and tags the commit with a tag named <release name>. If you don’t
  specify <commit id>, it uses the latest commit on develop.
* This commit-id must be on the develop branch.

Bump version in VERSION.txt
===========================

Edit the VERSION.txt file, bumping the digit appropriately:

* Major product milestone → increment by 1.0.0, e.g., 0.10.0 becomes 1.0.0.
* Task cards in the Release:Waiting column → increment by 0.1.0, e.g., 0.10.0 becomes 0.11.0
* Only bug cards in the Release:Waiting column → increment by 0.0.1, e.g., 0.10.0 becomes 0.10.1

Commit VERSION.txt::

  git commit VERSION.txt

Publish Release
===============

Push the release branch to the upstream repo (github)::

  git flow release publish <release name>


Merges the release branch back into 'master', tags the release with
its name, back-merges the release into 'develop', removes the release
branch::

  git flow release finish <release name>
  git push --tags

CircleCI and CodeDeploy do the Deployment
=========================================

The ``circle.yml`` file instructs circle to deploy commits from the
master branch to the CodeDeploy Deployment Group named “Prod”. This
group is the instances within the production ASG
``tttdiazoprod-TTTdiazoASG-.....``

This means that any commit on master which results in a successful
test run, will trigger a deployment to the production
environment. Circle doesn’t seem to let us specify tags limited to the
master branch, so we don’t want to deploy when the tag is first
created on the feature branch, but before the code gets to master.
