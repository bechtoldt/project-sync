#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIXME

Useful links:
* https://docs.npmjs.com/files/package.json
* https://www.npmjs.com/package/meta-json
* https://docs.npmjs.com/files/package.json
* https://docs.puppetlabs.com/puppet/latest/reference/modules_publishing.html
* https://robinpowered.com/blog/best-practice-system-for-organizing-and-tagging-github-issues/
"""

import collections
import jinja2
import json
import os
import subprocess
import sys
import yaml


def get_value_from_var(var, keys=[], default=None):
    if isinstance(keys, str):
        keys = [keys]

    for key in keys:
        if var.get(key, None):
            return var.get(key)
    return default


def process_templates(templates_dir, template_file, dest_path, data):
    t = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_dir),
        extensions=['jinja2.ext.autoescape'],
        autoescape=True)  # TODO optimize?
    template = t.get_template(template_file)

    contents = template.render(data)

    fh = open(dest_path, 'w')
    fh.write('{0}\n'.format(contents))
    fh.close()


def deep_merge(a, b, path=[]):  # original version: http://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                deep_merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            elif (a[key] is None and b[key] is not None) or (a[key] != b[key]):
                a[key] = b[key]
            elif b[key] is not None:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


class ProjectMetaData(collections.OrderedDict):
    def __init__(self):
        super(ProjectMetaData, self).__init__()

        self.standard_metadata_items = [
            'authors',  # Notice: This is not the same as maintainer
            'compatibility',
            'dependencies',
            'extra',  # TODO rename to misc?
            'license',  # use identifier from https://spdx.org/licenses/
            'maintainer',
            'name',
            'project_url',
            'source',
            'summary',
            'todo',
            'version',
        ]

    def load_file(self, file_path):
        file_name, file_type = os.path.splitext(file_path)

        if file_type == '.yaml':
            loader = yaml
        else:
            loader = json

        fh = open(file_path, 'r')
        stream = fh.read()
        fh.close()

        if file_type == '.json':
            data = loader.loads(stream)
        else:
            data = loader.load(stream)

        self.update_metadata(data)

    def update_metadata(self, raw_data):
        data = {}
        for item in self.standard_metadata_items:
            item_value = get_value_from_var(raw_data, item)
            if item_value is not None:
                data[item] = item_value

        deep_merge(self, data)

    def finalize_metadata(self):
        for item in self.standard_metadata_items:
            if item in self.keys():
                pass
            else:
                self[item] = None


class Project(object):
    def __init__(self, metadata=ProjectMetaData(), project_dir=None):
        self.metadata = metadata
        self.metadata['project_dir'] = project_dir

    def get_metadata_file(self):
        project_dir = self.metadata.get('project_dir')

        for file_type in ['yaml', 'json']:
            if os.path.isfile('{0}/meta.{1}'.format(project_dir, file_type)):
                return '{0}/meta.{1}'.format(project_dir, file_type)
            elif os.path.isfile('{0}/meta.{1}'.format(project_dir, file_type)):
                return '{0}/meta.{1}'.format(project_dir, file_type)

    def get_vcs_authors(self):
        args = ['git', 'log', '--format=\'%aN <%aE>\'']
        cmd = ' '.join(args)
        p = subprocess.Popen(args=cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.metadata['project_dir'])
        b_stdout, b_stderr = p.communicate()
        stdout = b_stdout.decode('utf-8')
        if stdout:
            return sorted(set(stdout.rstrip('\n').split('\n')))
        else:
            return []

    def update_metadata(self, metadata_file_path=None):
        if metadata_file_path is None:
            self.metadata.load_file(self.get_metadata_file())
        else:
            self.metadata.load_file(metadata_file_path)

    def dump_metadata(self):
        self.metadata.finalize_metadata()
        if not self.metadata['authors']:
            self.metadata['authors'] = self.get_vcs_authors()
        return self.metadata


def main(argv):
    # ~/Documents/dev/github/project-sync/projectsync/projectsync.py \
    # . \
    # ~/Documents/dev/github/project-sync/templates/arbe_saltstack \
    # ~/Documents/dev/github/project-sync/templates/arbe_saltstack/meta_defaults.yaml

    project_dir = argv[1]
    templates_dir = argv[2]
    metadata_defaults_file_path = argv[3] or None

    project = Project(project_dir=project_dir)
    project.update_metadata(metadata_defaults_file_path)
    project.update_metadata()

    metadata = project.dump_metadata()
    #pprint(metadata)

    for template_file in ['README.rst.jinja', 'LICENSE.jinja']:  # TODO get rid of template
        file_name, file_type = os.path.splitext(template_file)
        dest_path = '{0}/{1}'.format(project_dir, file_name)

        #pprint(data)
        process_templates(templates_dir, template_file, dest_path, metadata)


if __name__ == '__main__':
    main(sys.argv)
