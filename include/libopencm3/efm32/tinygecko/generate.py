#!/usr/bin/env python

import yaml
import logging
import textwrap

def commentblock(*textblocks, **formatargs):
    ret = []
    ret.extend(textwrap.wrap(textblocks[0].format(**formatargs), 80, initial_indent="/** ", subsequent_indent=" * "))
    last_block_was_at = textblocks[0].startswith('@')
    for b in textblocks[1:]:
        if not (last_block_was_at and b.startswith('@')):
            ret.append(" *")
        # FIXME: some blocks don't like being wrapped, eg @defgroup
        ret.extend(textwrap.wrap(b.format(**formatargs), 80, initial_indent=" * ", subsequent_indent=" * "))
        last_block_was_at = b.startswith('@')
    return "\n".join(ret) + "\n */\n"

def yaml2h(filenamebase):
    headername = "%s.h"%filenamebase
    yamlname = "%s.yaml"%filenamebase
    conveniencename = "%s.convenienceheaders"%filenamebase

    logging.info("Generating %s from %s", headername, yamlname)

    data = yaml.load(open(yamlname))
    # some defaults
    data.setdefault("projectname", "libopencm3")
    data.setdefault("includeguard", "LIBOPENCM3_EFM32_TINYGECKO_%s_H"%data['shortname'])

    with open(headername, 'w') as outfile:
        def wc(*args, **kwargs): # wrap "outfile" and "data" (as default) arguments  -- i'm a lazy typer
            final_kwargs = data.copy()
            final_kwargs.update(kwargs)
            outfile.write(commentblock(*args, **final_kwargs))
        def wc_close():
            outfile.write("/** @} */\n")
        def nl(): outfile.write("\n")
        def define(key, value, comment=None):
            outfile.write("#define ")
            outfile.write(key)
            outfile.write(" "*max(24-len(key), 1))
            outfile.write(str(value))
            if comment is not None:
                outfile.write(" /**< %s */"%comment)
            nl()

        outfile.write(licensedata[data['license']].format(**data))
        nl()
        wc("@file", "@see {shortdocname}")
        nl()
        wc("Definitions for the {shortname} subsystem ({longname}).", "This corresponds to the description in {baseref}.", "@defgroup {shortdocname} {longdocname}", "@{{")
        nl()
        outfile.write("#ifndef {includeguard}\n#define {includeguard}\n".format(**data))
        nl()
        outfile.write("#include <libopencm3/cm3/common.h>\n#include <libopencm3/efm32/memorymap.h>\n")
        nl()
        wc("Register definitions and register value definitions for the {shortname} subsystem", "@defgroup {shortdocname}_regsandvals {longdocname} registers and values", "@{{")
        nl()

        regs = data['registers']
        wc("These definitions reflect {baseref}{registers_baserefext}", "@defgroup {shortdocname}_registers {longdocname} registers", "@{{")
        nl()
        for regdata in regs:
            define("%s_%s"%(data['shortname'], regdata['name']), "MMIO32(%s_BASE + %#.003x)"%(data['shortname'], regdata['offset']), "@see %s_%s_%s"%(data['shortdocname'], regdata['name'], 'values' if 'values' in regdata else 'bits'))
        nl()
        wc_close() # close register definitions
        nl()
        for regdata in regs:
            has_bits = "fields" in regdata
            has_values = "values" in regdata
            if not has_bits and not has_values:
                continue

            wc("%s for the {shortname}_{name} register"%("Bit states" if has_bits else "Values"), "See {baseref}{definition_baserefext} for definitions"+regdata.get("details", "."), '@defgroup {shortdocname}_{name}_%s {longdocname} {name} %s'%(('bits' if has_bits else 'values',)*2), '@{{', **regdata)
            nl()

            if has_bits:
                for field in regdata['fields']:
                    #shiftdefine = "_%s_%s_%s_shift"%(shortname, regdata['name'], field['name'])
                    #define(shiftdefine, field['shift'])
                    if "values" in field:
                        for value in field.get("values"):
                            define("%s_%s_%s_%s"%(data['shortname'], regdata['name'], field['name'], value['name']), "(%s<<%s)"%(value['value'], field['shift']), value.get('doc', None))
                    else:
                        if field.get('length', 1) == 1:
                            define("%s_%s_%s"%(data['shortname'], regdata['name'], field['name']), "(1<<%s)"%field['shift'], field.get('doc', None))
                        else:
                            # FIXME: this should require the 'type' parameter to be set on this field
                            outfile.write("/* No values defined for the field %s */\n"%field['name'])
                    # FIXME: define mask
            else:
                for value in regdata['values']:
                    define("%s_%s_%s"%(data['shortname'], regdata['name'], value['name']), value['value'], value.get('doc', None))

            nl()
            wc_close()
            nl()
        wc_close() # close registers and values
        nl()

        outfile.write(open(conveniencename).read())

        nl()
        wc_close() # close convenience
        nl()
        outfile.write("#endif\n")

if __name__ == "__main__":
    licensedata = yaml.load(open("generate-license.yaml"))
    for basename in yaml.load(open('generate.yaml')):
        yaml2h(basename)
