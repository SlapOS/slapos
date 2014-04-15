These recipes provide the ability to save some buildout parameters and their value in a custom file, inside the instance folder.

In both recipes, you HAVE TO give a filename, which will be stored at the root of the instance folder


WriteRecipe : 
-------------

* Is used to create a section (named according to the buildout section_name).
* You can give then as much parameters you wish, with their default values.
* Whenever you run buildout, if the parameter has yet been saved in the config file, it will do nothing.
* If the parameter's value has changed in the config file, it won't be overwritten
* /!\ If you decide to change the default value of one parameter, ALL other parameters will be reseted in the config file, even if you changed it manually. Explanation : The default values aren't expected to change, except while development purposes.

ReadRecipe :

* It fills its own section with all the options in all the sections of the config file.
