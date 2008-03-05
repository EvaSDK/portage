#!/usr/bin/env python
# Copyright 1999-2007 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Id$

import os, re, sys

egrep_compat_map = {
	"[:alnum:]" : r'\w',
	"[:digit:]" : r'\d',
	"[:space:]" : r'\s',
}

here_doc_re = re.compile(r'.*\s<<[-]?(\w+)$')
func_start_re = re.compile(r'^[-\w]+\s*\(\)\s*$')
func_end_re = re.compile(r'^\}$')

var_assign_re = re.compile(r'(^|^declare\s+-\S+\s+|^export\s+)([^=\s]+)=("|\')?.*$')
close_quote_re = re.compile(r'(\\"|"|\')\s*$')

def compile_egrep_pattern(s):
	for k, v in egrep_compat_map.iteritems():
		s = s.replace(k, v)
	return re.compile(s)

def have_end_quote(quote, line):
	"""
	Check if the line has an end quote (useful for handling multi-line
	quotes). This handles escaped double quotes that may occur at the
	end of a line. The posix spec does not allow escaping of single
	quotes inside of single quotes, so that case is not handled.
	"""
	close_quote_match = close_quote_re.search(line)
	return close_quote_match is not None and \
		close_quote_match.group(1) == quote

def filter_bash_environment(pattern, file_in, file_out):
	here_doc_delim = None
	in_func = None
	multi_line_quote = None
	multi_line_quote_filter = None
	for line in file_in:
		if multi_line_quote is not None:
			if not multi_line_quote_filter:
				file_out.write(line)
			if have_end_quote(multi_line_quote, line):
				multi_line_quote = None
				multi_line_quote_filter = None
			continue
		if here_doc_delim is None and in_func is None:
			var_assign_match = var_assign_re.match(line)
			if var_assign_match is not None:
				quote = var_assign_match.group(3)
				filter_this = pattern.match(var_assign_match.group(2)) \
					is not None
				if quote is not None and not have_end_quote(quote, line):
					multi_line_quote = quote
					multi_line_quote_filter = filter_this
				if not filter_this:
					file_out.write(line)
				continue
		if here_doc_delim is not None:
			if here_doc_delim.match(line):
				here_doc_delim = None
			file_out.write(line)
			continue
		here_doc = here_doc_re.match(line)
		if here_doc is not None:
			here_doc_delim = re.compile("^%s$" % here_doc.group(1))
			file_out.write(line)
			continue
		# Note: here-documents are handled before fuctions since otherwise
		# it would be possible for the content of a here-document to be
		# mistaken as the end of a function.
		if in_func:
			if func_end_re.match(line) is not None:
				in_func = None
			file_out.write(line)
			continue
		in_func = func_start_re.match(line)
		if in_func is not None:
			file_out.write(line)
			continue
		# This line is not recognized as part of a variable assignment,
		# function definition, or here document, so just allow it to
		# pass through.
		file_out.write(line)

if __name__ == "__main__":
	description = "Filter out variable assignments for varable " + \
		"names matching a given PATTERN " + \
		"while leaving bash function definitions and here-documents " + \
		"intact. The PATTERN should use python regular expression syntax" + \
		" but [:digit:], [:space:] and " + \
		"[:alnum:] character classes will be automatically translated " + \
		"for compatibility with egrep syntax."
	usage = "usage: %s PATTERN" % os.path.basename(sys.argv[0])
	from optparse import OptionParser
	parser = OptionParser(description=description, usage=usage)
	options, args = parser.parse_args(sys.argv[1:])
	if len(args) != 1:
		parser.error("Missing required PATTERN argument.")
	file_in = sys.stdin
	file_out = sys.stdout
	filter_bash_environment(
		compile_egrep_pattern(args[0]), file_in, file_out)
	file_out.flush()
