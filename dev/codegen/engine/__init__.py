# Portable OpenAPI → SDK codegen engine.
#
# Everything here is host-agnostic: given a parsed spec IR (:mod:`tochka.codegen.parser`)
# and the small Tochka config tables (:mod:`tochka.codegen.config`), it builds and emits the
# generated surface. Lift the whole ``codegen/`` package elsewhere and swap ``config`` +
# ``fetch`` + ``parser`` to retarget another OpenAPI-described API.
