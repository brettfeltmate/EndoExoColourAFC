from klibs.KLIndependentVariable import IndependentVariableSet

EndoExoColourAFC_ind_vars = IndependentVariableSet()


# Indicates if alerting signal involves a shift in intensity (volume)
EndoExoColourAFC_ind_vars.add_variable('signal_intensity', str)
EndoExoColourAFC_ind_vars['signal_intensity'].add_values('lo', 'hi')

# Time between cue onset (visual & audio) and target onset
EndoExoColourAFC_ind_vars.add_variable('cue_value', str)
EndoExoColourAFC_ind_vars['cue_value'].add_values('short', 'long')

# Indicates if cue accurately reflects target onset
EndoExoColourAFC_ind_vars.add_variable('cue_valid', str)
EndoExoColourAFC_ind_vars['cue_valid'].add_values(("valid", 8), "invalid_short", "invalid_long")

# Indicates if catch or true trial
EndoExoColourAFC_ind_vars.add_variable('catch_trial', bool)
EndoExoColourAFC_ind_vars['catch_trial'].add_values((False, 3), True)



