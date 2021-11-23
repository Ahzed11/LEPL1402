import os
import random
import string
import shutil
import re

script_dir = os.path.abspath(os.path.dirname(__file__))

source_dir = os.path.join(script_dir, 'src', 'main', 'java')
test_dir = os.path.join(script_dir, 'src', 'test', 'java')

inginious_dir = os.path.join(script_dir, 'inginious')
templates_dir = os.path.join(script_dir, 'templates')

map_archive_id = {}

course_name = 'LEPL1402-0821'

def _safe_mkdir(directory, delete=False):
    if not os.path.exists(directory):
        os.mkdir(directory)
    elif delete:
        shutil.rmtree(directory)
        os.mkdir(directory)


def get_dir_from_exercices(exs):
    return course_name + '_'.join(exs)


def get_exercises():
    """Get the list of exercises from the source directory"""
    files = [f for f in os.listdir(source_dir)]
    exercises = [os.path.splitext(os.path.basename(f))[0] for f in files
                 if os.path.isfile(os.path.join(source_dir, f))]
    return exercises


def strip_file(filename, outfile=None):
    lines = open(filename, 'r').readlines()
    out = filename if outfile is None else outfile
    with open(out, 'w') as fout:
        pruning = False
        for line in lines:
            if "BEGIN STRIP" in line:
                pruning = True
                continue
            elif "END STRIP" in line:
                pruning = False
                continue
            if not pruning:
                fout.write(line.replace("// STUDENT", ""))


def strip_directory(path):
    for file in os.listdir(path):
        strip_file(os.path.join(path, file))


def create_archive(exercise):
    """Generate an archive for the given exercise"""
    dst_dir = os.path.join(script_dir, exercise)
    source_dst = os.path.join(dst_dir, 'src', 'main', 'java')
    test_dst = os.path.join(dst_dir, 'src', 'test', 'java')
    os.mkdir(dst_dir)
    os.makedirs(source_dst, exist_ok=True)
    os.makedirs(test_dst, exist_ok=True)

    shutil.copyfile(os.path.join(script_dir, 'pom.xml'),
                    os.path.join(dst_dir, 'pom.xml'))

    src = exercise + '.java'
    test = exercise + 'Test.java'
    shutil.copyfile(os.path.join(source_dir, src),
                    os.path.join(source_dst, src))
    shutil.copyfile(os.path.join(test_dir, test),
                    os.path.join(test_dst, test))

    archive_id = ''.join(random.choice(string.ascii_letters) for _ in range(20))
    map_archive_id[exercise] = archive_id
    archive_path = dst_dir + '-' + archive_id

    strip_directory(source_dst)
    strip_directory(test_dst)

    shutil.make_archive(archive_path, 'zip', './', './' + exercise)
    # Move the archive into the public directory for download
    exercise_dir = os.path.join(inginious_dir, exercise)
    shutil.move(archive_path + '.zip', os.path.join(exercise_dir, 'public'))
    shutil.rmtree(dst_dir)


def createTestFile(exercise, exercise_dir):
    inname = exercise + 'Test.java'
    outname = exercise + 'TestInginious.java'
    outfile = open(os.path.join(exercise_dir, outname), 'w')
    with open(os.path.join(test_dir, inname)) as f:
        buffer = list()
        in_test = False
        count_open_acc = 0
        for line in f:
            if line.startswith(f'public class {exercise}Test'):
                outfile.write('import com.github.guillaumederval.javagrading.*;\n')
                outfile.write(line.replace(f'{exercise}Test', f'{exercise}TestInginious'))
            elif '@Test' in line:
                outfile.write(line)
                outfile.write('\t@Grade(value=1, cpuTimeout=1000)\n')
                in_test = True
            elif in_test:
                count_open_acc += line.count('{')
                count_open_acc -= line.count('}')
                if count_open_acc == 0:
                    # End of the test function
                    in_test = False
                    for buffered_line in buffer:
                        outfile.write(buffered_line)
                    outfile.write(line)
                    buffer = list()
                else:
                    if 'assert' in line:
                        rgx = re.match('.*"(.*)".*', line)
                        if rgx is not None:
                            assertMsg = rgx.group(1)
                            outfile.write(f'\t@GradeFeedback(message="{assertMsg}", onFail=true)\n')
                    buffer.append(line)
            else:
                outfile.write(line)
    outfile.close()


def create_exercise_task(exercise):
    exercise_dir = os.path.join(inginious_dir, exercise)
    _safe_mkdir(exercise_dir)
    _safe_mkdir(os.path.join(exercise_dir, 'public'))

    # copy libs
    shutil.copytree(os.path.join(templates_dir, 'libs'),
                    os.path.join(exercise_dir, 'libs'))

    # Copy the test file to the src directory
    createTestFile(exercise, exercise_dir)

    # Test runner
    runner_file = 'RunTests.java'
    with open(os.path.join(templates_dir, runner_file), 'r') as f:
        test_runner_content = ''.join(f.readlines())

    with open(os.path.join(exercise_dir, runner_file), 'w') as f:
        f.write(test_runner_content.format(exercise + 'TestInginious'))

    # Run file
    run_file = 'run'
    with open(os.path.join(templates_dir, run_file), 'r') as f:
        run_content = ''.join(f.readlines())

    with open(os.path.join(exercise_dir, run_file), 'w') as f:
        f.write(run_content.format(exercise))


    # write the template file
    with open(os.path.join(exercise_dir, exercise + '.java'), 'w') as f:
        f.write('@@code@@')

    create_archive(exercise)

    exercise_id = exercises.index(exercise)
    with open(os.path.join(exercise_dir, 'task.yaml'), 'w') as f:
        f.write(task_config_tpl.format(
            course_name,
            exercise,
            exercise + '-' + map_archive_id[exercise] + '.zip',
            exercise_id))


def generate_inginious_tasks():
    """Generate the INGInious tasks
    """
    for exercise in exercises:
        create_exercise_task(exercise)

def generate_course_yaml():
    with open(os.path.join(templates_dir, 'course.yaml.tpl'), 'r') as f:
              tpl = ''.join(f.readlines())
    nb_section = int(input("Number of sections: "))
    question_per_section = int(input("Number of question shown per sections: "))
    exercises_per_section = [list() for _ in range(nb_section)]
    print("Select for each excercise its section. Sections are index from 0, you can exclude an exercise by putting -1")
    for exercise in exercises:
        sec = int(input(exercise + ": "))
        if sec != -1:
            exercises_per_section[sec].append(exercise)
    dispenser_data = ""
    for sec_id in range(nb_section):
        task_list = '\n'.join([' '*12 + f'{ex}: {i}' for i, ex in enumerate(exercises_per_section[sec_id])])
        dispenser_data += f"""
    -   config:
            amount: {question_per_section}
        id: q{sec_id+1}
        rank: {sec_id}
        tasks_list:
{task_list}
        title: Question {sec_id + 1}
"""
    with open(os.path.join(inginious_dir, 'course.yaml'), 'w') as f:
        f.write(tpl.format(dispenser_data))


def create_inginious_dir():
    _safe_mkdir(inginious_dir, delete=True)

if __name__ == '__main__':
    exercises = get_exercises()
    with open(os.path.join(templates_dir, 'task.yaml.tpl'), 'r') as f:
        task_config_tpl = ''.join(f.readlines())
    create_inginious_dir()
    generate_inginious_tasks()
    generate_course_yaml()