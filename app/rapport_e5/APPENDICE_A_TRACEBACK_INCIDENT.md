# Appendice A — Traceback de l'incident

Cet appendice doit etre lu avec le rapport principal. Il reproduit le traceback reel observe lors de la soumission d'une image de 600x600 pixels a la route `/predict`.

## Traceback complet

```text
Traceback (most recent call last):
  File ".../flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File ".../flask/app.py", line 902, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)
  File ".../app/app.py", line 131, in predict
    probs = model.predict(img_array, verbose=0)[0]
  File ".../keras/src/utils/traceback_utils.py", line 122, in error_handler
    raise e.with_traceback(filtered_tb) from None
  File ".../keras/src/layers/input_spec.py", line 245, in assert_input_compatibility
    raise ValueError(
ValueError: Input 0 of layer "functional_1" is incompatible with the layer:
  expected shape=(None, 224, 224, 3), found shape=(1, 600, 600, 3)
```