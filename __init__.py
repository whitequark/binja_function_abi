import binaryninja as bn
import binaryninja.enums as bne
import binaryninja.interaction as bni

def get_function_defined_or_referred_at(view, addr):
    # https://github.com/Vector35/binaryninja-api/issues/916
    if view.plat is None:
        return None

    func = view.get_function_at(addr)
    if func is not None:
        return func

    for func in view.get_functions_containing(addr) or []:
        for const in func.get_constants_referenced_by(addr):
            referee = view.get_function_at(const.value)
            if referee is not None:
                return referee

def abi_dialog(view, addr):
    func = get_function_defined_or_referred_at(view, addr)

    def show_error(text):
        bni.show_message_box("ABI Error", text, icon=bne.MessageBoxIcon.ErrorIcon)

    arch = view.platform.arch
    cconvs = view.platform.calling_conventions
    cconv_names = map(lambda x: x.name, cconvs)
    cconv = func.calling_convention
    clobbers = set(func.clobbered_regs)
    cconv_clobbers = set([cconv.int_return_reg] + cconv.int_arg_regs + cconv.caller_saved_regs)
    add_clobbers = clobbers.difference(cconv_clobbers)
    remove_clobbers = cconv_clobbers.difference(clobbers)

    cconv_field = bni.ChoiceField("Calling convention", cconv_names)
    cconv_field.result = cconvs.index(cconv)
    cconv_current_field = "(current: {})".format(cconv)

    add_clobber_field = bni.TextLineField("Additional clobbers")
    add_clobber_field.result = " ".join(list(map(str, add_clobbers)))
    add_clobber_current_field = "(current: {})".format(add_clobber_field.result)

    remove_clobber_field = bni.TextLineField("Excluded clobbers")
    remove_clobber_field.result = " ".join(list(map(str, remove_clobbers)))
    remove_clobber_current_field = "(current: {})".format(remove_clobber_field.result)

    fields = [
        "Note: it's not currently possible to pre-fill the fields,",
        "so please manually set the ones you don't want to change to current values",
        cconv_field, cconv_current_field,
        add_clobber_field, add_clobber_current_field,
        remove_clobber_field, remove_clobber_current_field
    ]
    if bni.get_form_input(fields, "Function ABI"):
        cconv = cconvs[cconv_field.result]

        add_clobbers = set(add_clobber_field.result.split())
        remove_clobbers = set(remove_clobber_field.result.split())
        for reg in add_clobbers | remove_clobbers:
            if reg not in arch.regs:
                show_error("{} is not a valid {} register.".format(reg, arch.name))
                return

        func.calling_convention = cconv

        clobbers = set([cconv.int_return_reg] + cconv.int_arg_regs + cconv.caller_saved_regs)
        clobbers.update(add_clobbers)
        clobbers.difference_update(remove_clobbers)
        func.clobbered_regs = list(clobbers)

def has_function_at(view, addr):
    return get_function_defined_or_referred_at(view, addr) is not None

bn.PluginCommand.register_for_address(
    'Function ABI...', 'View or change detailed ABI of this function.', abi_dialog, has_function_at
)
