export let inputsTS1 = 
`  <div class="grid grid-cols-12 sm:gap-6">
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <p class="mb-2 text-muted">Basic Input:</p>
    <input type="text" class="form-control" id="input">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-label" class="form-label">Form Input With Label</label>
    <input type="text" class="form-control" id="input-label">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-placeholder" class="form-label">Form Input With Placeholder</label>
    <input type="text" class="form-control" id="input-placeholder" placeholder="Placeholder">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-text" class="form-label">Type Text</label>
    <input type="text" class="form-control" id="input-text" placeholder="Text">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-number" class="form-label">Type Number</label>
    <input type="number" class="form-control" id="input-number" placeholder="Number">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-password" class="form-label">Type Password</label>
    <input type="password" class="form-control" id="input-password" placeholder="Password">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-email" class="form-label">Type Email</label>
    <input type="email" class="form-control" id="input-email" placeholder="Email&#64;xyz.com">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-tel" class="form-label">Type Tel</label>
    <input type="tel" class="form-control" id="input-tel" placeholder="+1100-2031-1233">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-date" class="form-label">Type Date</label>
    <input type="date" class="form-control" id="input-date">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-week" class="form-label">Type Week</label>
    <input type="week" class="form-control" id="input-week">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-month" class="form-label">Type Month</label>
    <input type="month" class="form-control" id="input-month">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-time" class="form-label">Type Time</label>
    <input type="time" class="form-control" id="input-time">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-datetime-local" class="form-label">Type datetime-local</label>
    <input type="datetime-local" class="form-control" id="input-datetime-local">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-search" class="form-label">Type Search</label>
    <input type="search" class="form-control" id="input-search" placeholder="Search">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-submit" class="form-label">Type Submit</label>
    <input type="submit" class="form-control ti-btn" id="input-submit" value="Submit">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-reset" class="form-label">Type Reset</label>
    <input type="reset" class="form-control ti-btn" id="input-reset">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-button" class="form-label">Type Button</label>
    <input type="button" class="form-control ti-btn !text-white !bg-primary" id="input-button"  value="Button">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <div class="grid grid-cols-12 gap-6">
        <div class="xl:col-span-3 col-span-12 flex flex-col ">
            <label class="form-label">Type Color</label>
            <input class="form-control form-input-color !rounded-md" type="color" value="#136bd0">
        </div>
        <div class="xl:col-span-5 col-span-12">
            <div class="form-check">
                <p class="mb-3 px-0 text-muted">Type Checkbox</p>
                <input class="form-check-input ms-2" type="checkbox" value="" checked>
            </div>
        </div>
        <div class="xl:col-span-4 col-span-12">
            <div class="form-check">
                <p class="mb-4 px-0 text-muted">Type Radio</p>
                <input class="form-check-input ms-2" type="radio" checked>
            </div>
        </div>
    </div>
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <div>
        <label for="file-input" class="sr-only">Type file</label>
        <input type="file" name="file-input" id="file-input" class="block w-full border border-gray-200 focus:shadow-sm dark:focus:shadow-white/10 rounded-sm text-sm focus:z-10 focus:outline-0 focus:border-gray-200 dark:focus:border-white/10 dark:border-white/10
         file:border-0
        file:bg-gray-200 file:me-4
        file:py-3 file:px-4
        dark:file:bg-black/20 dark:file:text-white/50">
      </div>
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label class="form-label">Type Url</label>
    <input class="form-control" type="url"  name="website" placeholder="http://example.com">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-disabled" class="form-label">Type Disabled</label>
    <input type="text" id="input-disabled" class="form-control" placeholder="Disabled input" disabled>
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-readonlytext" class="form-label">Input Readonly Text</label>
    <input type="text" readonly class="form-control-plaintext" id="input-readonlytext" value="email&#64;example.com">
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="disabled-readonlytext" class="form-label">Disabled Readonly Input</label>
    <input class="form-control" type="text" value="Disabled readonly input" id="disabled-readonlytext" aria-label="Disabled input example" disabled readonly>
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label class="form-label">Type Readonly Input</label>
    <input class="form-control" type="text" value="Readonly input here..." aria-label="readonly input example" readonly>
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="text-area" class="form-label">Textarea</label>
    <textarea class="form-control" id="text-area" rows="1"></textarea>
</div>
<div class="xl:col-span-4 lg:col-span-6 md:col-span-6 sm:col-span-12 col-span-12">
    <label for="input-DataList" class="form-label">Datalist example</label>
    <input class="form-control" type="text" list="datalistOptions" id="input-DataList" placeholder="Type to search...">
    <datalist id="datalistOptions">
        <option value="San Francisco">
        </option>
        <option value="New York">
        </option>
        <option value="Seattle">
        </option>
        <option value="Los Angeles">
        </option>
        <option value="Chicago">
        </option>
    </datalist>
</div>
</div>`
export let inputsTS2 = 
`    <div class="grid grid-cols-12 gap-y-3">
<div class="xl:col-span-12 col-span-12">
    <label for="input-noradius" class="form-label">Input With No Radius</label>
    <input type="text" class="form-control !rounded-none" id="input-noradius" placeholder="No Radius">
</div>
<div class="xl:col-span-12 col-span-12">
    <label for="input-rounded" class="form-label">Input With Radius</label>
    <input type="text" class="form-control" id="input-rounded" placeholder="Default Radius">
</div>
<div class="xl:col-span-12 col-span-12">
    <label for="input-rounded-pill" class="form-label">Rounded Input</label>
    <input type="text" class="form-control !rounded-full" id="input-rounded-pill" placeholder="Rounded">
</div>
</div>`
export let inputsTS3 = 
` <div class="grid grid-cols-12 gap-y-3">
<div class="xl:col-span-12 col-span-12">
    <label for="input-rounded1" class="form-label">Default</label>
    <input type="text" class="form-control" id="input-rounded1" placeholder="Default">
</div>
<div class="xl:col-span-12 col-span-12">
    <label for="input-rounded2" class="form-label">Dotted Input</label>
    <input type="text" class="form-control border-dotted" id="input-rounded2" placeholder="Dotted">
</div>
<div class="xl:col-span-12 col-span-12">
    <label for="input-rounded3" class="form-label">Dashed Input</label>
    <input type="text" class="form-control border-dashed" id="input-rounded3" placeholder="Dashed">
</div>
</div>`
export let inputsTS4 =
`    <input class="form-control form-control-sm mb-3" type="text"
placeholder=".form-control-sm" aria-label=".form-control-sm example">
<input class="form-control mb-3" type="text" placeholder="Default input"
    aria-label="default input example">
<input class="form-control form-control-lg" type="text"
placeholder=".form-control-lg" aria-label=".form-control-lg example">
`
export let inputsTS5 =
` <form>
<div class="mb-3">
    <label for="exampleInputEmail1" class="form-label">Email
        address</label>
    <input type="email" class="form-control" id="exampleInputEmail1"
        aria-describedby="emailHelp">
    <div id="emailHelp" class="form-text">We'll
        never share your email
        with
        anyone else.</div>
</div>
<div class="mb-3">
    <label for="exampleInputPassword1" class="form-label">Password</label>
    <input type="password" class="form-control" id="exampleInputPassword1">
</div>
<div class="mb-3 form-check !ps-0">
    <input type="checkbox" class="form-check-input" id="exampleCheck1">
    <label class="form-check-label ps-2" for="exampleCheck1">Check
        me out</label>
</div>
<button type="submit" class="ti-btn ti-btn-primary-full">Submit</button>
</form>`
export let inputsTS6 =
`   <div class="box-body">
<label for="inputPassword5" class="form-label">Password</label>
<input type="password" id="inputPassword5" class="form-control"
    aria-describedby="passwordHelpBlock">
<div id="passwordHelpBlock" class="form-text">
    Your password must be 8-20 characters long, contain letters and
    numbers,
    and
    must not contain spaces, special characters, or emoji.
</div>
</div>`
export let inputsTS7 =
`    <div class="sm:grid grid-cols-12 gap-4 items-center">
<div class="xxxl:col-span-1 col-span-2">
    <label for="inputPassword6" class="col-form-label">Password</label>
</div>
<div class="col-span-3">
    <input type="password" id="inputPassword6" class="form-control"
        aria-describedby="passwordHelpInline">
</div>
<div class="col-span-7">
    <span id="passwordHelpInline" class="form-text">
        Must be 8-20 characters long.
    </span>
</div>
</div>`
export let inputsTS8 =
`  <form>
<fieldset disabled>
    <legend class="text-2xl">Disabled fieldset example</legend>
    <div class="mb-3">
        <label for="disabledTextInput" class="form-label">Disabled
            input</label>
        <input type="text" id="disabledTextInput" class="form-control"
            placeholder="Disabled input">
    </div>
    <div class="mb-3">
        <label for="disabledSelect" class="form-label">Disabled select
            menu</label>
        <select id="disabledSelect" class="form-select">
            <option>Disabled select</option>
        </select>
    </div>
    <div class="mb-3">
        <div class="form-check !ps-0">
            <input class="form-check-input" type="checkbox"
                id="disabledFieldsetCheck" disabled>
            <label class="form-check-label ps-2" for="disabledFieldsetCheck">
                Can't check this
            </label>
        </div>
    </div>
    <button type="submit" class="ti-btn ti-btn-primary-full opacity-[0.6]">Submit</button>
</fieldset>
</form>`