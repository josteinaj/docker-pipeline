# Docker Pipeline (experimental!)

*Docker Pipeline* is a basic tool that lets you set up
a chain of docker images as a data processing pipeline.
The goal is easy setup, configuration and maintenance
of data processing pipelines.

## Roadmap

v0.1:
- [x] Everything is defined in a single YAML file.
- [x] No dependencies other than Docker. Is itself a docker image.
- [x] Chain docker images to create data pipelines. (i.e. parse yaml and chain list of steps)
- [x] Testing with `test`
- [x] The `dockerfile` instruction (useful while developing)

v0.2:
- [x] Tests with name `*` should run for all tests
- [x] Testing with `assert` as alias for `test` with `*`  and `status`

v0.3:
- [ ] full support for pipeline definition grammar
  - [ ] support `if`, `elif` and `else`
  - [x] support `foreach`
  - [x] support `unfold`
  - [ ] support `synchronized`
  - [ ] support `exit`

v0.4:
- [ ] Watches a folder for new input files and directories. Automatically passes it into the pipeline.

v0.5:
- [ ] Send messages to Slack channel.
- [ ] View live-updated status webpage
  - [ ] showing which containers are running at each step
  - [ ] showing what data is in each running container in the pipeline
  - [ ] how much CPU/memory is used by each docker container
  - [ ] showing last 10 processed items

v0.6:
- [ ] Pipelines with no input can be triggered with HTTP POST/GET requests.

v0.7:
- [ ] Ability to delegate processing to other servers than localhost.

v0.8:
- [ ] Support multiple pipelines

## Docker image requirements

To work in a pipeline, the docker image must follow the following conventions:

- /mnt/config/ used for providing configuration settings to the images (read only)
- /mnt/input/ used for retrieving files and folders from the preceding step in the pipeline (read only)
- /mnt/output/ used for passing files and folders to the next step in the pipeline
- /mnt/status/ used for outputting values to docker pipeline conditionals
- a ENTRYPOINT which will be used to run the image

## Creating a docker pipeline

### Steps

A basic pipeline consists of a list of docker image references.
You may also use the `dockerfile` instruction, which lets you
bundle Dockerfiles with the pipeline instead of using images.
The `dockerfile` instruction is mainly useful for development
as building the docker images takes time.

### Conditionals and status strings

All lines from all files in the status directory are used as the set of status strings.
The status strings can be used for conditional processing using `if`.
The `if` block will be executed if one of the status strings matches
the string in the `if`. The same goes for `elif`. This means that the
set of status strings may match more than one `if`/`elif` statement,
so the order of the statements matter.

### Multiple outputs

If an image has multiple outputs, and you want to process those outputs
separately, the `foreach` statement can be used. `foreach` will list
all top-level files and folders in the output directory of the preceding
step, and provide those files one-by-one as input to the next step.

The `foreach` statement creates a *sub-pipeline*. The sub-pipelines might
be run in parallel. Example:

```yaml
  - step
  - step
  - foreach:
      - step
      - step
  - step
  - step
```

When all the files or folders that `foreach` are
iterating over have been run through the sub-pipeline, the outputs
from all those sub-pipelines are joined back together and provided as
input to the next step in the pipeline.

This output will consist of a series folders named after files or
folders that were iterated over. So for instance, if you iterate over
`index.html`, `audio.mp3` and `images/`, then the combined output will
consist of three folders: `index.html/`, `audio.mp3/` and `images/`.
This may not always be what you want, and for those cases you can
use the `unfold` statement to "unfold" these sub-folders. The `unfold`
statement takes a integer value, which is the depth you want to unfold.
In most cases that will be 1. If you choose to `unfold` the output of
`foreach`, note that files that are not below the nesting depth will
be removed, and if there are file naming collisions there is no
guarantee as to which file will be provided in the unfolded output.
Example:

```yaml
  - unfold: 1
```

### Synchronized blocks

If part of the pipeline cannot have multiple executions of itself running
in parallel, the `synchronized` statement can be used. This will
guarantee that there will be only one item passing through the
sub-pipeline inside the `synchronized` block.

### Stopping execution

The `exit` instructioncan be used to stop execution of the pipeline.
Combine it with `if` to conditionally stop execution.

### Testing pipelines

To test pipelines, use the `assert` and `test` instructions.
These instructions are ignored during normal use.

The `tests` subdirectory in the directory containing the `pipeline.yml`
file can contain test data. The directories inside this
test data directory can be referenced using the `test` instruction:

```yaml
  - test:
      input: input-1
      expect: expect-1
```

In this example, the `input-1` and `expect-1` are directories inside
the `tests` directory of your project.

`status` can be used to declare the expected status as this point in the execution:

```yaml
  - test:
      input: input-1
      status: success
```

`context` can be used to evaluate this test only if the name of the
context matches the given `context`. This is especially useful inside a `foreach`.

The `assert` instruction is a syntactic shortcut for checking the status
at this point in the execution. The following `assert` and `test` is equivalent:

```yaml
  - test:
      input: '*'
      status: success
  
  - assert: success
```

When testing, the pipeline is run once for every unique `input`
directory used in `test` instructions in the pipeline. `test`
instructions using a different input directory than the one
currently being tested are skipped; otherwise the `test`
succeeds only if:
- if `expected` is used: the files in the `expected` directory is exactly
  the same as the ones the the output directory of the
  preceding step at this point in the execution.
- if `status` is used: the status at this point in the execution is the
  one stated in this test.

If `focus` is present in a `test`, then only tests with the same input
as that test will be tested. This is useful while developing to shorten
the time it takes to run the tests relevant for what you are working on.
For instance:

```yaml
  - test:
      input: 'input-1'
      status: success
      focus: true
```


### Example pipeline

```yaml
name: Example Pipeline
pipeline:
  
  # A pipeline consists of a list of steps,
  # the output of each step used as input for the next.
  # Each item is a reference do a docker image.
  - my/image1
  - my/image1
  
  # Use foreach to iterate through each
  # file and/or folder alphabetically
  - foreach:
    - my/image1
    - my/image1
    
    # Use test for testing pipelines
    - test:
        input: input-1
        expect: output-1
        iteration: file1
        status: success
  
  # After foreach, all files will be joined back into
  # one folder in directories with the same names as when
  # starting the foreach, before continuing execution.
  
  # Use if, elif and else to
  # conditionally run one or more steps
  - if blue:
    - my/image1
  - elif red:
    - my/image1
    - my/image1
  - else:
    - my/image1
  
  # Use synchronized around one or more steps that
  # requires that no more than one item is being
  # processed at once. No more than one item in
  # this block will be processed concurrently.
  - synchronized:
    - my/image1
    - my/image1
    
    # use assert for simple status tests while testing
    - assert success
  
  # @exit can be used to stop execution
  - if error:
    - exit
  
  # For the purpose of logging; if the first line
  # preceding a step is a comment, then that comment
  # will be used as the description for the step.
  # 
  # This line is the description for the following step.
  - my/image1
  
  # The output of the last step will go nowhere.
  # To output files from a pipeline, the containers
  # will have to mount shared folders or in some
  # other way pass data around to cause the
  # desired effects.
  - my/image1
```

## Running Docker Pipeline

```bash
docker run \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /my/pipeline/dir:/mnt/pipeline:ro \
    -v /my/config/dir:/mnt/config:ro \
    josteinaj/docker-pipeline /my/pipeline/dir
    # optionally append the argument 'test' to run tests
```

- The directory mounted as `/mnt/config`, if present, will be
  mounted as `/mnt/config` (read only) in all docker containers
  started in the pipeline.
- The directory mounted as `/mnt/input`, if present, will be
  monitored for new files and directories. Any new files or
  directories will be sent one-by-one to the pipeline for processing.
  Each file or directory will be mounted as `/mnt/input/file-or-dir-name`
  at the start of the pipeline.
- `/var/run/docker.sock` needs to be mounted so that
  docker-pipeline is able to run docker containers.
