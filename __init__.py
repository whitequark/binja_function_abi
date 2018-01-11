import binaryninja as bn
import binaryninja.enums as bne
import binaryninja.interaction as bni

def get_function_defined_or_referred_at(view, addr):
    func = view.get_function_at(addr)
    if func is not None:
        return func

    for func in view.get_functions_containing(addr) or []:
        for const in func.get_constants_referenced_by(addr):
            referee = view.get_function_at(const.value)
            if referee is not None:
                return referee

def change_abi(view, addr):
    func = get_function_defined_or_referred_at(view, addr)

    def show_error(text):
        bni.show_message_box("ABI Error", text, icon=bne.MessageBoxIcon.ErrorIcon)

    arch = view.platform.arch
    cconvs = view.platform.calling_conventions
    cconv_names = map(lambda x: x.name, cconvs)

    cconv_field = bni.ChoiceField("Calling convention", cconv_names)
    cconv_field.result = cconvs.index(func.calling_convention)

    add_clobber_field = bni.TextLineField("Additional clobbers")
    remove_clobber_field = bni.TextLineField("Exclude clobbers")

    fields = [cconv_field, add_clobber_field, remove_clobber_field]
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
    'Change ABI...', 'Change ABI of this function.', change_abi, has_function_at
)
